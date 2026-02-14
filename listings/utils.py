from django.utils.html import escape

class SafeDict(dict):
    def __missing__(self, key):
        return ""

def render_contract(tpl: str, data: dict, dynamic_keys: set) -> str:
    out = {}
    for k, v in data.items():
        val = "" if v is None else str(v)
        val = escape(val)

        if k in dynamic_keys:
            out[k] = f'<span class="dyn">{val}</span>'
        else:
            out[k] = val

    return tpl.format_map(SafeDict(out))
