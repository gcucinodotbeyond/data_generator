from .base import DialogueStep

class FarewellStep(DialogueStep):
    def execute(self, ctx, meta_contexts, **kwargs):
        is_success = ctx.get("ui_state", {}).get("state") == "purchased"
        sentiment = "positive" if is_success else "neutral"
        
        u_bye = self.turn_gen.render_utterance("farewell", ctx, sentiment=sentiment)
        self.turn_gen.add_turn(ctx, "user", u_bye)
        resp_farewell = self.turn_gen.render_utterance("assistant_responses", ctx, category="farewell")
        self.turn_gen.add_turn(ctx, "assistant", resp_farewell)
