from .base import DialogueStep

class DisabilityStep(DialogueStep):
    def execute(self, ctx, meta_contexts, **kwargs):
        """
        Handles the distinct turn where the user declares a disability
        and the assistant acknowledges it.
        """
        if ctx.get("disability_phrase"):
             u_dis = self.turn_gen.render_utterance("refinement", ctx, aspect="disability", 
                                                    disability_phrase=ctx.get("disability_phrase"))
             self.turn_gen.add_turn(ctx, "user", u_dis)
             
             # Assistant Acknowledgement
             resp = self.turn_gen.render_utterance("assistant_responses", ctx, category="disability_ack")
             self.turn_gen.add_turn(ctx, "assistant", resp)
