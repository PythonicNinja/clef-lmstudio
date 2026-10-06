"""Probability selection with clef-flash.

The model returns a distribution over a fixed option set ("Billing:80%"), not
just one answer. That turns a guess into a decision you can gate: act when the
top option is clearly ahead, ask a human when the distribution is flat.

LM Studio does not expose token logprobs for this model, so the distribution is
the model's own stated estimate, parsed and renormalised to sum to 1.
"""

import math
import re
import time
from dataclasses import dataclass

from clef_mlx import ClefFlash


@dataclass(frozen=True)
class Selection:
    probs: dict[str, float]  # option -> probability, sums to 1, sorted high to low
    latency_s: float

    @property
    def choice(self) -> str:
        return next(iter(self.probs))

    @property
    def confidence(self) -> float:
        return self.probs[self.choice]

    @property
    def margin(self) -> float:
        """Gap between the top two options; small = genuinely ambiguous."""
        top = list(self.probs.values())
        return top[0] - (top[1] if len(top) > 1 else 0.0)

    @property
    def entropy(self) -> float:
        """Normalised Shannon entropy: 0 = certain, 1 = uniform."""
        n = len(self.probs)
        h = -sum(p * math.log(p) for p in self.probs.values() if p > 0)
        return max(0.0, h / math.log(n)) if n > 1 else 0.0


class Undecided(Exception):
    """The model ran out of budget without committing to a distribution."""


class ProbabilitySelector:
    """Ask clef-flash for a probability over `options` and parse it."""

    def __init__(self, options: list[str], model: ClefFlash | None = None, max_tokens: int = 400):
        self.options = options
        self.model = model or ClefFlash()
        self.max_tokens = max_tokens  # bounds the model's reasoning; ambiguous cases spiral
        names = "|".join(re.escape(o) for o in sorted(options, key=len, reverse=True))
        self._line = re.compile(rf"\b({names})[^\d\n]{{0,6}}?(\d+(?:\.\d+)?)\s*%", re.I)

    def select(self, question: str, case: str) -> Selection:
        fmt = "\n".join(f"{o}:NN%" for o in self.options)
        prompt = (
            f'{question}\nCase: "{case}"\n'
            f"Give probability for each option: {', '.join(self.options)}.\n"
            f"Format exactly:\n{fmt}"
        )
        start = time.perf_counter()
        text = self.model.chat(prompt, temperature=0, max_tokens=self.max_tokens)
        latency = time.perf_counter() - start

        raw = {o: 0.0 for o in self.options}
        canon = {o.lower(): o for o in self.options}
        for name, pct in self._line.findall(text):  # last mention wins: final answer follows reasoning
            raw[canon[name.lower()]] = float(pct)
        total = sum(raw.values())
        if total == 0:
            raise Undecided(f"{latency:.1f}s, no distribution in: {text[:120]!r}…")
        probs = dict(sorted(((o, p / total) for o, p in raw.items()), key=lambda kv: -kv[1]))
        return Selection(probs, latency)


class Router:
    """Turn a Selection into an action: auto-route, or hand off when unsure."""

    def __init__(self, selector: ProbabilitySelector, min_confidence=0.7, min_margin=0.25):
        self.selector = selector
        self.min_confidence = min_confidence
        self.min_margin = min_margin

    def route(self, question: str, case: str) -> tuple[str, Selection | None]:
        try:
            s = self.selector.select(question, case)
        except Undecided as e:
            return f"HUMAN REVIEW (model undecided: {e})", None
        if s.confidence >= self.min_confidence and s.margin >= self.min_margin:
            return f"auto -> {s.choice}", s
        runner_up = list(s.probs)[1]
        return f"HUMAN REVIEW ({s.choice} vs {runner_up})", s


QUESTION = "Which support team should own this ticket?"
TEAMS = ["billing", "technical", "account-security", "sales", "spam"]
TICKETS = [
    "I was charged twice for my Pro plan this month. Please refund the duplicate.",
    "Production dashboard returns 502 for 10 minutes, 300 users blocked!!",
    "Do you offer nonprofit discounts? We'd need about 40 seats.",
    "Got a password reset I didn't request and a login from another country.",
    "CONGRATULATIONS you won a free iPhone click here bit.ly/xyz",
    "Upgraded to Enterprise but SSO still not working and the invoice looks wrong too.",
    "hey quick question about my account",
]


def bar(p: float, width: int = 20) -> str:
    return "#" * round(p * width)


def main() -> None:
    router = Router(ProbabilitySelector(TEAMS))
    for ticket in TICKETS:
        action, s = router.route(QUESTION, ticket)
        print(f"> {ticket}")
        if s:
            for opt, p in s.probs.items():
                if p > 0:
                    print(f"    {opt:<17}{p:6.1%} {bar(p)}")
            print(f"    margin={s.margin:.2f} entropy={s.entropy:.2f} ({s.latency_s:.1f}s)")
        print(f"    => {action}\n")


if __name__ == "__main__":
    main()
