import json
import logging

log = logging.getLogger("ey-forms")
log.setLevel(logging.DEBUG)

def get_api_keys(path: str):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception as e:
        log.error(e)

def above(p1, p2):
    lower_y_p1 = max(c['y'] for c in p1)
    upper_y_p2 = min(c['y'] for c in p2)
    return lower_y_p1  < upper_y_p2
    
def not_in(br1, br2s):
    return all(above(br1, br2) or above(br2, br1) for br2 in br2s)

def legal_non_empty_string(s):
    s = s.strip()
    s = s.strip('-')
    if not s:
        return False
    try:
        float(s)
        return False
    except ValueError:
        try:
            int(s)
            return False
        except ValueError:
            pass
    return True



def jsonify_dict2(d):
    """
    Handle the case where keys (of possibly nested dicts) are not json-native datatypes, e.g.
    they are tuples. Handles by (recursively) encoding key values into strings if necessary.
    """
    def encode_key(k):
        if isinstance(k, (str,int,float,bool)):
            return k
        return f"$$enc_{k}"
    
    return {encode_key(k): jsonify_dict2(v) if isinstance(v, dict) else v
            for k, v in d.items()}

def unjsonify_dict2(d):
    """
    Reverse the jsonify_dict(.) transformation. 
    """
    def decode_key(k):
        if isinstance(k, (int,float,bool)):
            return k
        assert isinstance(k, str)
        return eval(k[len('$$enc_'):]) if k.startswith('$$enc_') else k
    return {decode_key(k): unjsonify_dict2(v) if isinstance(v, dict) else v
            for k, v in d.items()}