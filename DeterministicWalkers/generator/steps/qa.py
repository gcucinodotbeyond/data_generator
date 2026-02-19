from .base import DialogueStep

class QAStep(DialogueStep):
    def execute(self, ctx, meta_contexts, **kwargs):
        q, a, topic = self.ctx_mgr.get_contextual_qa(ctx)
        if q and a:
            u_text = self.turn_gen.render_utterance("qa", ctx, question=q, topic=topic)
            self.turn_gen.add_turn(ctx, "user", u_text)
            self.turn_gen.add_turn(ctx, "assistant", a)
            return True
        return False
