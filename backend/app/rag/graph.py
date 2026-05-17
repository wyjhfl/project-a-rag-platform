import re
from dataclasses import dataclass, field
from typing import Callable, Protocol

from app.rag.chunker import DocumentChunk

Relation = tuple[str, str, str]


class Neo4jDriver(Protocol):
    def session(self, database: str | None = None):
        ...

    def close(self) -> None:
        ...


DriverFactory = Callable[[str, tuple[str, str]], Neo4jDriver]


@dataclass
class LocalGraphRetriever:
    """Small in-memory graph retriever for equipment/fault/part relations."""

    _chunks: list[DocumentChunk] = field(default_factory=list)
    _relations: set[Relation] = field(default_factory=set)
    _entity_to_chunks: dict[str, list[DocumentChunk]] = field(default_factory=dict)

    def index_chunks(self, chunks: list[DocumentChunk]) -> None:
        self._chunks = chunks
        self._relations.clear()
        self._entity_to_chunks.clear()

        for chunk in chunks:
            entities = self._extract_entities(chunk.content, str(chunk.metadata.get("source", "")))
            for entity in entities:
                self._entity_to_chunks.setdefault(entity, []).append(chunk)

            for device in entities.devices:
                for fault in entities.fault_codes:
                    self._relations.add((device, "HAS_FAULT", fault))
            for fault in entities.fault_codes:
                for part in entities.parts:
                    self._relations.add((fault, "MAY_CHECK_PART", part))
                for action in entities.actions:
                    self._relations.add((fault, "HAS_ACTION", action))

    def search(self, query: str, top_k: int = 4) -> list[DocumentChunk]:
        query_entities = self._extract_entities(query, source="")
        seeds = set(query_entities.devices | query_entities.fault_codes | query_entities.parts)
        if not seeds:
            return []

        related = set(seeds)
        for source, _, target in self._relations:
            if source in seeds or target in seeds:
                related.add(source)
                related.add(target)

        scores: dict[tuple[str, int], float] = {}
        chunks: dict[tuple[str, int], DocumentChunk] = {}
        for entity in related:
            for chunk in self._entity_to_chunks.get(entity, []):
                if not self._chunk_matches_query_seed(chunk, seeds):
                    continue
                key = (
                    str(chunk.metadata.get("source", "")),
                    int(chunk.metadata.get("chunk_index", 0)),
                )
                chunks[key] = chunk
                scores[key] = scores.get(key, 0.0) + self._entity_weight(entity, seeds)

        ordered_keys = sorted(scores, key=lambda key: scores[key], reverse=True)
        return [chunks[key] for key in ordered_keys[:top_k]]

    def relations(self) -> set[Relation]:
        return set(self._relations)

    def _extract_entities(self, text: str, source: str) -> "GraphEntities":
        haystack = f"{source}\n{text}"
        return GraphEntities(
            devices=self._extract_device_models(haystack),
            fault_codes=self._extract_fault_codes(haystack),
            parts=self._extract_parts(haystack),
            actions=self._extract_actions(haystack),
        )

    def _extract_device_models(self, text: str) -> set[str]:
        patterns = [
            r"\bUPS[-_]?\d+[A-Z]?\b",
            r"\bVFD[-_]?\d{2,4}\b",
            r"\bVFD\d{2,4}\b",
            r"\bPFX\d{2,4}\b",
            r"\bPLC[-_]?[A-Z]?\d{2,4}\b",
            r"\bCW\d{2,4}\b",
            r"\bA\d{2,4}\b",
        ]
        return {
            match.group(0).upper()
            for pattern in patterns
            for match in re.finditer(pattern, text, flags=re.IGNORECASE)
        }

    def _extract_fault_codes(self, text: str) -> set[str]:
        codes: set[str] = set()
        for match in re.finditer(r"\b[A-Z]{0,4}[-_]?\d{2,4}\b", text, flags=re.IGNORECASE):
            code = match.group(0).upper()
            if code.startswith(("A", "CW", "PLC", "VFD", "UPS", "PFX")):
                continue
            if re.search(r"[A-Z]", code):
                codes.add(code)
        return codes

    def _extract_parts(self, text: str) -> set[str]:
        known_parts = [
            "过滤器",
            "进气过滤器",
            "压力传感器",
            "供压管路",
            "管路",
            "冷凝器",
            "冷凝风机",
            "过滤网",
            "水泵",
            "电池",
            "风扇",
            "散热器",
        ]
        parts = {part for part in known_parts if part in text}
        if "进气过滤器" in parts:
            parts.add("过滤器")
        return parts

    def _extract_actions(self, text: str) -> set[str]:
        known_actions = [
            "检查",
            "清洗",
            "停机",
            "隔离",
            "人工确认",
            "升级人工",
            "校准",
            "更换",
        ]
        return {action for action in known_actions if action in text}

    def _entity_weight(self, entity: str, seeds: set[str]) -> float:
        if entity in seeds:
            return 3.0
        if any(char.isdigit() for char in entity):
            return 2.0
        return 1.0

    def _chunk_matches_query_seed(self, chunk: DocumentChunk, seeds: set[str]) -> bool:
        haystack = f"{chunk.metadata.get('source', '')}\n{chunk.content}"
        normalized = self._normalize_entity_text(haystack)
        return any(
            seed in haystack or self._normalize_entity_text(seed) in normalized
            for seed in seeds
        )

    def _normalize_entity_text(self, text: str) -> str:
        return re.sub(r"[^A-Z0-9\u4e00-\u9fff]", "", text.upper())


@dataclass(frozen=True)
class GraphEntities:
    devices: set[str]
    fault_codes: set[str]
    parts: set[str]
    actions: set[str]

    def __iter__(self):
        yield from self.devices
        yield from self.fault_codes
        yield from self.parts
        yield from self.actions


class Neo4jGraphRetriever:
    """Neo4j-backed graph retriever with the same extraction rules as the local fallback."""

    def __init__(
        self,
        uri: str,
        username: str,
        password: str,
        database: str | None = None,
        driver_factory: DriverFactory | None = None,
    ) -> None:
        self.database = database
        self._extractor = LocalGraphRetriever()
        if driver_factory:
            self.driver = driver_factory(uri, (username, password))
        else:
            self.driver = self._create_driver(uri, username, password)

    def index_chunks(self, chunks: list[DocumentChunk]) -> None:
        with self.driver.session(database=self.database) as session:
            for chunk in chunks:
                entities = self._extractor._extract_entities(
                    chunk.content,
                    str(chunk.metadata.get("source", "")),
                )
                chunk_payload = self._chunk_payload(chunk)
                for device in entities.devices:
                    for fault in entities.fault_codes:
                        session.run(
                            """
                            MERGE (device:Device {name: $device})
                            MERGE (fault:Fault {code: $fault})
                            MERGE (device)-[:HAS_FAULT]->(fault)
                            """,
                            device=device,
                            fault=fault,
                        )
                for fault in entities.fault_codes:
                    for part in entities.parts:
                        session.run(
                            """
                            MERGE (fault:Fault {code: $fault})
                            MERGE (part:Part {name: $part})
                            MERGE (fault)-[:MAY_CHECK_PART]->(part)
                            """,
                            fault=fault,
                            part=part,
                        )
                    for action in entities.actions:
                        session.run(
                            """
                            MERGE (fault:Fault {code: $fault})
                            MERGE (action:Action {name: $action})
                            MERGE (fault)-[:HAS_ACTION]->(action)
                            """,
                            fault=fault,
                            action=action,
                        )
                for entity in entities:
                    session.run(
                        """
                        MERGE (chunk:Chunk {key: $key})
                        SET chunk.source = $source,
                            chunk.chunk_index = $chunk_index,
                            chunk.content = $content
                        MERGE (entity:Entity {name: $entity})
                        MERGE (entity)-[:MENTIONED_IN]->(chunk)
                        """,
                        entity=entity,
                        **chunk_payload,
                    )

    def search(self, query: str, top_k: int = 4) -> list[DocumentChunk]:
        entities = self._extractor._extract_entities(query, source="")
        seeds = sorted(entities.devices | entities.fault_codes | entities.parts)
        if not seeds:
            return []

        with self.driver.session(database=self.database) as session:
            records = session.run(
                """
                MATCH (entity)
                WHERE entity.name IN $entities OR entity.code IN $entities
                MATCH (entity)-[*1..2]-(chunk:Chunk)
                RETURN DISTINCT chunk.source AS source,
                       chunk.chunk_index AS chunk_index,
                       chunk.content AS content
                LIMIT $top_k
                """,
                entities=seeds,
                top_k=top_k,
            )
            return [
                DocumentChunk(
                    content=str(record["content"]),
                    metadata={
                        "source": str(record["source"]),
                        "document_id": str(record["source"]),
                        "chunk_index": int(record["chunk_index"]),
                        "retrieval_source": "neo4j",
                    },
                )
                for record in records
            ]

    def close(self) -> None:
        self.driver.close()

    def _create_driver(self, uri: str, username: str, password: str) -> Neo4jDriver:
        try:
            from neo4j import GraphDatabase
        except ImportError as exc:
            raise RuntimeError(
                "Neo4j driver is not installed. Install the optional 'neo4j' package "
                "or pass a driver_factory for tests."
            ) from exc
        return GraphDatabase.driver(uri, auth=(username, password))

    def _chunk_payload(self, chunk: DocumentChunk) -> dict:
        source = str(chunk.metadata.get("source", ""))
        chunk_index = int(chunk.metadata.get("chunk_index", 0))
        return {
            "key": f"{source}:{chunk_index}",
            "source": source,
            "chunk_index": chunk_index,
            "content": chunk.content,
        }
