import logging
from df_engine.core import Context, Actor
import common.dff.integration.context as int_ctx

logger = logging.getLogger(__name__)

DEFAULT_RESPONSE = "Okay. Why did you send me this picture?"
DEFAULT_CONFIDENCE = 0.85
SUPER_CONFIDENCE = 1.0


def generic_response(ctx: Context, actor: Actor, excluded_skills=None, *args, **kwargs) -> str:
    caption = int_ctx.get_last_human_utterance(ctx, actor).get("annotations", {}).get("fromage", {})

    logger.debug(f"fromage image skill {caption}")
    int_ctx.set_confidence(ctx, actor, DEFAULT_CONFIDENCE)
    return caption
