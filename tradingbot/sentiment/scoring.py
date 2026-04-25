import logging
from typing import List

_torch = None
_tokenizer = None
_model = None
_device = None


labels = ["positive", "negative", "neutral"]
LOGGER = logging.getLogger(__name__)


def _load_finbert():
    global _torch, _tokenizer, _model, _device
    if _model is not None and _tokenizer is not None and _torch is not None:
        return _torch, _tokenizer, _model, _device

    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    _torch = torch
    _device = "cuda:0" if torch.cuda.is_available() else "cpu"
    _tokenizer = AutoTokenizer.from_pretrained("ProsusAI/finbert")
    _model = AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert").to(_device)
    _model.eval()
    return _torch, _tokenizer, _model, _device

def estimate_sentiment(news):
    if news:
        try:
            torch, tokenizer, model, device = _load_finbert()
        except (ImportError, ModuleNotFoundError) as exc:
            LOGGER.warning("FinBERT dependencies unavailable; using neutral sentiment fallback. Error: %s", exc)
            return 0, labels[-1]
        except Exception as exc:
            LOGGER.warning("FinBERT sentiment load failed; using neutral sentiment fallback. Error: %s", exc)
            return 0, labels[-1]
        # Tokenize input and move tokens to the correct device
        tokens = tokenizer(news, return_tensors="pt", padding=True).to(device)

        # Perform inference without gradient tracking to keep live GPU memory stable.
        with torch.no_grad():
            result = model(tokens["input_ids"], attention_mask=tokens["attention_mask"])["logits"]

        # Move the result to CPU for further processing, if needed
        result = torch.nn.functional.softmax(torch.sum(result, 0), dim=-1)
        probability = result[torch.argmax(result)]
        sentiment = labels[torch.argmax(result)]
        return probability, sentiment
    else:
        return 0, labels[-1]


def score_headline(headline: str) -> float:
    if not headline:
        return 0.0
    probability, sentiment = estimate_sentiment([headline])
    probability_value = float(probability)
    if sentiment == "positive":
        return probability_value
    if sentiment == "negative":
        return -probability_value
    return 0.0


def score_headlines(headlines: List[str]) -> List[float]:
    return [score_headline(headline) for headline in headlines]

if __name__ == "__main__":
    tensor, sentiment = estimate_sentiment(['markets responded negatively to the news!', 'traders were displeased!'])
    print(tensor, sentiment)
    torch, _, _, _ = _load_finbert()
    print("CUDA available:", torch.cuda.is_available())
