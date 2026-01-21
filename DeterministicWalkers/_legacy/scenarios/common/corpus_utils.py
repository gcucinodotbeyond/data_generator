
from typing import List, Dict, Optional, Any
from core.random import SeededRandom
from scenarios.common.llm_client import LLMClient

# Global instance to avoid reloading config every time
_llm_client = None

def get_llm_client() -> LLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client

def select_best_match(
    rng: SeededRandom, 
    items: List[Dict], 
    criteria: Optional[Dict[str, str]] = None,
    enable_llm_fallback: bool = True
) -> Dict:
    """
    Selects a corpus item matching the criteria with fallback logic.
    
    Fallback Order:
    1. Exact Match
    2. Drop 'complexity'
    3. Drop 'register'
    4. Drop 'tone'
    5. LLM Rewrite (if enabled) using a random item
    6. Random Item (Raw)
    """
    if not items:
        return {"text": ""}
        
    # If no criteria, just pick random
    if not criteria:
        return rng.choice(items)
        
    # Helper to check match
    def matches(item: Dict, curr_criteria: Dict[str, str]) -> bool:
        attrs = item.get('attributes', {})
        if not attrs: return False
        for k, v in curr_criteria.items():
            if attrs.get(k) != v:
                return False
        return True

    # 1. Exact Match
    candidates = [i for i in items if matches(i, criteria)]
    if candidates:
        return rng.choice(candidates)
        
    # 2. Drop Complexity
    if 'complexity' in criteria:
        relaxed_1 = criteria.copy()
        del relaxed_1['complexity']
        candidates = [i for i in items if matches(i, relaxed_1)]
        if candidates:
            return rng.choice(candidates)
            
    # 3. Drop Register (User requested this order: complexity -> register -> tone)
    # So we drop register from the *already relaxed* set (no complexity) or original if complexity wasn't there
    relaxed_2 = criteria.copy()
    if 'complexity' in relaxed_2: del relaxed_2['complexity']
    if 'register' in relaxed_2:
        del relaxed_2['register']
        candidates = [i for i in items if matches(i, relaxed_2)]
        if candidates:
            return rng.choice(candidates)
            
    # 4. Drop Tone
    relaxed_3 = relaxed_2.copy()
    if 'tone' in relaxed_3:
        del relaxed_3['tone']
        candidates = [i for i in items if matches(i, relaxed_3)]
        if candidates:
            return rng.choice(candidates)
            
    # 5. LLM Fallback
    # Pick a random item found in the category (even if mismatch)
    fallback_item = rng.choice(items)
    original_text = fallback_item.get('text', '') if isinstance(fallback_item, dict) else str(fallback_item)
    
    if enable_llm_fallback:
        try:
            client = get_llm_client()
            # We rewrite the RANDOM fallback item to match the ORIGINAL criteria
            new_text = client.rewrite_text(original_text, criteria)
            if new_text and new_text != original_text:
                # Return a synthetic item
                return {
                    **fallback_item,
                    "text": new_text,
                    "attributes": criteria,  # It now matches!
                    "is_synthetic": True
                }
        except Exception as e:
            print(f"Fallback generation failed: {e}")
            
            
    # 6. Final Fail-safe
    return fallback_item

def get_templatized_text(item: Dict) -> str:
    """
    Convert item text to a template by replacing extracted slots with placeholders.
    e.g. "Roma termini" -> "{destination}"
    """
    if not isinstance(item, dict):
        return str(item)
        
    text = item.get('text', '')
    slots = item.get('extracted_slots', {})
    
    if not slots:
        return text
        
    # Sort slots by value length descending to prevent partial replacements
    # e.g. "Roma Termini" (len 12) before "Roma" (len 4)
    sorted_slots = sorted(slots.items(), key=lambda x: len(str(x[1])), reverse=True)
    
    for key, value in sorted_slots:
        if not value: continue
        val_str = str(value)
        # Simple case-insensitive replacement
        # We try to preserve case of the original text if possible, but for simple template replacement
        # a direct case-insensitive search-replace is robust enough for now.
        
        # Check if value is actually in text
        idx = text.lower().find(val_str.lower())
        if idx != -1:
            # Get variable name e.g. {destination}
            # Only do it if not already a placeholder
            if "{" + key + "}" not in text:
                # We replace the ACTUAL substring found to preserve surrounding context
                original_substring = text[idx : idx + len(val_str)]
                text = text.replace(original_substring, "{" + key + "}")
                
    return text
