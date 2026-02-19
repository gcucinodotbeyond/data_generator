import random
import json
import os
import re

class DialogueFlowBuilder:
    def __init__(self, context_manager, turn_generator, steps, distribution=None):
        self.ctx_mgr = context_manager
        self.turn_gen = turn_generator
        self.steps = steps
        self.distribution = distribution or {}
        self.scenario_dir = os.path.join(os.path.dirname(__file__), '..', 'scenarios')

    def build_dynamic_flow(self, run_id, try_interruption_cb, ood_starters, ood_followups):
        # Default scenario steps
        scenario_steps = ["greeting", "search", "selection_purchase", "farewell"]
        scenario_name = "default"
        
        # Scenario Selection based on distribution
        if self.distribution.get("scenario_distribution") and os.path.exists(self.scenario_dir):
            dist = self.distribution["scenario_distribution"]
            population = [p for p in dist.keys() if os.path.exists(os.path.join(self.scenario_dir, f"{p}.txt"))]
            weights = [dist[p] for p in population]
            
            if population:
                scenario_name = random.choices(population, weights=weights, k=1)[0]
                scenario_path = os.path.join(self.scenario_dir, f"{scenario_name}.txt")
                with open(scenario_path, 'r', encoding='utf-8') as f:
                    scenario_steps = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        elif os.path.exists(self.scenario_dir):
            all_files = [f for f in os.listdir(self.scenario_dir) if f.endswith(".txt")]
            if all_files:
                scenario_file = random.choice(all_files)
                scenario_name = scenario_file.replace(".txt", "")
                scenario_path = os.path.join(self.scenario_dir, scenario_file)
                with open(scenario_path, 'r', encoding='utf-8') as f:
                    scenario_steps = [line.strip() for line in f if line.strip() and not line.startswith("#")]

        print(f"[Dialogue] Run {run_id} using scenario: '{scenario_name}'")
        
        ctx = self.ctx_mgr.init_context(run_id)
        meta_contexts = []

        for raw_line in scenario_steps:
            sub_steps = [s.strip() for s in raw_line.split("+")]
            for sub_step in sub_steps:
                step = sub_step
                param = None
                if "(" in sub_step and ")" in sub_step:
                    match = re.search(r"([^(]+)\s*\(([^)]+)\)", sub_step)
                    if match:
                        step = match.group(1).strip()
                        param = match.group(2).strip()
                
                if param:
                    ctx["topic"] = param

                # Dynamic Step Execution (OCP)
                if step in self.steps:
                    # Prepare arguments for steps that need them
                    step_args = {
                        "try_interruption": try_interruption_cb,
                        "ood_starters": ood_starters,
                        "ood_followups": ood_followups,
                        "starter": len(ctx["generated_messages"]) <= 1
                    }
                    
                    result = self.steps[step].execute(ctx, meta_contexts, **step_args)
                    
                    # Handle return value (standardize True/False/None)
                    # Search step returns False to break
                    if step == "search" and result is False:
                        break
                else:
                    print(f"Warning: Step '{step}' not found in configuration.")
        
        ctx["scenario_name"] = scenario_name
        return self.finalize(ctx, meta_contexts)

    def finalize(self, ctx, meta_contexts):
        for snap in meta_contexts:
            if isinstance(snap["params"]["ui_state"], dict):
                 snap["params"]["ui_state"] = json.dumps(snap["params"]["ui_state"])
            if isinstance(snap["params"]["trains_array"], list):
                 snap["params"]["trains_array"] = json.dumps(snap["params"]["trains_array"])

        metadata = {
            "generator_version": "dynamic_v3",
            "scenario": ctx.get("scenario_name", "default"), 
            "seed": random.randint(1000,999999), 
            "run_id": ctx["run_id"],
            "rudeness": ctx["rudeness"],
            "verbose": ctx.get("verbose", "standard"),
            "interaction": {
                "origin": ctx.get("origin", ""),
                "destination": ctx.get("destination", ""),
                "passengers": ctx.get("passengers", 1),
                "extras": {
                    "pet_small": ctx.get("pet_count", 0) if ctx.get("pet_type") == "small" else 0,
                    "pet_big": ctx.get("pet_count", 0) if ctx.get("pet_type") == "large" else 0,
                    "pet_assistant": ctx.get("pet_count", 0) if ctx.get("pet_type") == "assistance" else 0,
                    "bike_normal": ctx.get("bike_count", 0) if ctx.get("bike_type") == "normal" else 0,
                    "bike_foldable": ctx.get("bike_count", 0) if ctx.get("bike_type") == "foldable" else 0
                }
            },
            "user_profile": {
                "preferences": ctx.get("seat_preference", []), 
                "disabilities": ctx.get("disability_type") 
            },
            "contexts": meta_contexts
        }

        return {
            "tools": "{{TOOL_DEFINITION}}",
            "messages": ctx["generated_messages"],
            "_meta": metadata
        }
