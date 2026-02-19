from .base import DialogueStep

class GreetingStep(DialogueStep):
    def execute(self, ctx, meta_contexts, **kwargs):
        u_greet = self.turn_gen.render_utterance("greeting", ctx)
        self.turn_gen.add_turn(ctx, "user", u_greet)
        resp = self.turn_gen.render_utterance("assistant_responses", ctx, category="greeting_response")
        self.turn_gen.add_turn(ctx, "assistant", resp)
