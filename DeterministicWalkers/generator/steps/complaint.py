from .base import DialogueStep

class ComplaintStep(DialogueStep):
    def execute(self, ctx, meta_contexts, **kwargs):
        u_complaint = self.turn_gen.render_utterance("complaint", ctx)
        self.turn_gen.add_turn(ctx, "user", u_complaint)
        resp = self.turn_gen.render_utterance("assistant_responses", ctx, category="complaint_response")
        self.turn_gen.add_turn(ctx, "assistant", resp)
