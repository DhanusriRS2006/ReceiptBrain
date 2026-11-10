
import litellm

_original_completion = litellm.completion

def _groq_compatible_completion(*args, **kwargs):
    model = kwargs.get("model", "")

    if isinstance(model, str) and model.startswith("groq/"):
        messages = kwargs.get("messages", [])

        kwargs["messages"] = [
            {
                key: value
                for key, value in message.items()
                if key != "cache_breakpoint"
            }
            for message in messages
        ]

    return _original_completion(*args, **kwargs)

def enable_groq_compat():
    if litellm.completion is not _groq_compatible_completion:
        litellm.completion = _groq_compatible_completion
