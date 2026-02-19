import random
from .base import DialogueStep

class OODStep(DialogueStep):
    def execute(self, ctx, meta_contexts, **kwargs):
        starter = kwargs.get("starter", False)
        ood_starters = kwargs.get("ood_starters")
        ood_followups = kwargs.get("ood_followups")
        if starter:
            if ood_starters:
                q = random.choice(ood_starters)
                u_ood = self.turn_gen.render_utterance("ood", ctx, question=q)
                self.turn_gen.add_turn(ctx, "user", u_ood)
                resp = self.turn_gen.render_utterance("assistant_responses", ctx, category="ood_redirect")
                self.turn_gen.add_turn(ctx, "assistant", resp)
                return True
        else:
            if ood_followups:
                q = random.choice(ood_followups)
                u_text = self.turn_gen.render_utterance("ood", ctx, question=q)
                self.turn_gen.add_turn(ctx, "user", u_text)
                
                resp = self.turn_gen.render_utterance("assistant_responses", ctx, category="ood_redirect")
                self.turn_gen.add_turn(ctx, "assistant", resp)
                return True
        return False
