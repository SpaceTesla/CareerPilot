from __future__ import annotations

from app.core.logging import get_logger
from app.services.neo4j_service import Neo4jService

logger = get_logger(__name__)


class CareerGraphAnalyticsService:
    """
    Retrieves and analyzes career trajectory graphs and skill adjacency clusters in Neo4j.
    """

    @classmethod
    async def find_career_paths(cls, start_role: str, target_role: str, max_depth: int = 2) -> list[dict]:
        """
        Finds the most frequent career transition paths from start_role to target_role.
        """
        query = (
            f"MATCH p = (start:Role {{name: $start_role}})-[r:TRANSITIONED_TO*1..{int(max_depth)}]->(target:Role {{name: $target_role}}) "
            "RETURN p"
        )
        paths_output = []
        async with Neo4jService.get_session() as session:
            try:
                result = await session.run(query, start_role=start_role, target_role=target_role)
                async for record in result:
                    path = record["p"]
                    steps = []
                    path_probabilities = []

                    nodes = path.nodes
                    relationships = path.relationships

                    for i, rel in enumerate(relationships):
                        source_node = nodes[i]
                        target_node = nodes[i + 1]

                        source_name = source_node.get("name")
                        target_name = target_node.get("name")

                        avg_duration = rel.get("avg_duration_months", 12.0)
                        confidence = rel.get("confidence", 0.5)

                        # Query bridge skills for the target role
                        skills_res = await session.run(
                            "MATCH (ro:Role {name: $target_name})-[req:REQUIRES_SKILL]->(s:Skill) "
                            "RETURN s.canonical_name AS skill_name "
                            "ORDER BY req.relevance_score DESC "
                            "LIMIT 3",
                            target_name=target_name,
                        )
                        bridge_skills = [sk["skill_name"] async for sk in skills_res]

                        steps.append(
                            {
                                "step_index": i,
                                "source_role": source_name,
                                "target_role": target_name,
                                "avg_transition_time_months": float(avg_duration),
                                "common_bridge_skills": bridge_skills,
                                "confidence_score": float(confidence),
                            }
                        )
                        path_probabilities.append(float(confidence))

                    path_prob = 1.0
                    for p_val in path_probabilities:
                        path_prob *= p_val
                    path_prob = round(path_prob, 2)

                    paths_output.append({"steps": steps, "path_probability": path_prob})
            except Exception as e:
                logger.error(f"Error querying career paths in Neo4j: {e}")

        paths_output.sort(key=lambda x: x["path_probability"], reverse=True)
        return paths_output

    @classmethod
    async def get_related_skills(cls, skill_name: str) -> list[dict]:
        """
        Retrieves related skills based on profile co-occurrences.
        """
        query = (
            "MATCH (s:Skill {canonical_name: $skill_name}) "
            "MATCH (s)<-[:HAS_SKILL]-(p:CandidateProfile)-[:HAS_SKILL]->(other:Skill) "
            "WHERE other.canonical_name <> s.canonical_name "
            "RETURN other.canonical_name as skill_name, count(p) as weight "
            "ORDER BY weight DESC "
            "LIMIT 5"
        )
        related = []
        async with Neo4jService.get_session() as session:
            try:
                result = await session.run(query, skill_name=skill_name)
                async for record in result:
                    name = record["skill_name"]
                    w = record["weight"]

                    # Normalize score to be between 0.0 and 1.0
                    normalized_weight = round(min(1.0, 0.5 + (w * 0.05)), 2)

                    rel_type = "CO_OCCURRENCE"
                    if normalized_weight > 0.85:
                        rel_type = "SPECIALIZATION_OF"
                    elif normalized_weight > 0.75:
                        rel_type = "COMPATIBLE_WITH"

                    related.append(
                        {
                            "skill_name": name,
                            "relationship": rel_type,
                            "weight": normalized_weight,
                        }
                    )
            except Exception as e:
                logger.error(f"Error querying related skills in Neo4j: {e}")
        return related
