"""Automated feedback loop — re-runs failed outputs with learnings applied."""
import logging
import time

logger = logging.getLogger("clay-webhook-os")


class FeedbackLoop:
    """Automates the re-run cycle when thumbs-down feedback is received.

    Flow:
    1. User gives thumbs-down with notes
    2. Learning engine extracts insight (existing)
    3. This module auto-queues a re-run with learnings applied
    4. Stores comparison (before/after) for review
    """

    def __init__(self):
        self._reruns: dict[str, dict] = {}  # job_id → {original, rerun, status, ...}

    async def trigger_rerun(
        self,
        job_id: str,
        original_result: dict,
        skill: str,
        data: dict,
        instructions: str | None,
        model: str,
        feedback_note: str,
        pool,
        learning_engine=None,
        memory_store=None,
        context_index=None,
    ) -> dict:
        """Queue a re-run incorporating feedback learnings."""
        from app.core.context_assembler import build_prompt
        from app.core.skill_loader import load_context_files, load_skill

        # Load skill and build prompt with learnings injected
        skill_content = load_skill(skill)
        if skill_content is None:
            return {"error": True, "error_message": f"Skill '{skill}' not found for rerun"}

        context_files = load_context_files(skill_content, data, skill_name=skill)

        # Add explicit correction instruction
        augmented_instructions = instructions or ""
        augmented_instructions += f"\n\n[CORRECTION FROM FEEDBACK]: {feedback_note}"

        prompt = build_prompt(
            skill_content, context_files, data, augmented_instructions,
            memory_store=memory_store,
            context_index=context_index,
            learning_engine=learning_engine,
        )

        start = time.time()
        try:
            result = await pool.submit(prompt, model)
            duration_ms = int((time.time() - start) * 1000)

            rerun_record = {
                "job_id": job_id,
                "skill": skill,
                "original_result": original_result,
                "rerun_result": result.get("result", {}),
                "feedback_note": feedback_note,
                "duration_ms": duration_ms,
                "status": "completed",
                "created_at": time.time(),
            }
            self._reruns[job_id] = rerun_record
            logger.info("[feedback-loop] Re-run completed for job %s (skill=%s)", job_id, skill)
            return rerun_record

        except Exception as e:
            logger.error("[feedback-loop] Re-run failed for job %s: %s", job_id, e)
            return {
                "job_id": job_id,
                "status": "failed",
                "error": str(e),
            }

    def get_rerun(self, job_id: str) -> dict | None:
        """Get a re-run comparison for a job."""
        return self._reruns.get(job_id)

    def get_all_reruns(self, limit: int = 50) -> list[dict]:
        """Get recent reruns."""
        items = sorted(self._reruns.values(), key=lambda x: x.get("created_at", 0), reverse=True)
        return items[:limit]

    def get_stats(self) -> dict:
        total = len(self._reruns)
        completed = sum(1 for r in self._reruns.values() if r.get("status") == "completed")
        return {
            "total_reruns": total,
            "completed": completed,
            "failed": total - completed,
        }
