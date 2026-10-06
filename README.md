# clef-lmstudio

Small Python client and examples for the `clef-flash` model served by LM Studio's
OpenAI-compatible API (`http://localhost:1234/v1`).

## Quick start

1. In LM Studio, download and load `clef-flash`, then start the server
   (Developer tab → Start Server, or `lms server start`). It listens on port 1234.
2. Check the model is served:
   ```
   curl -s localhost:1234/v1/models | grep clef-flash
   ```
3. Create the venv (skip if `env/` already exists):
   ```
   python3 -m venv env
   env/bin/pip install openai
   ```
4. Run:
   ```
   env/bin/python main.py       # plain + streamed call
   env/bin/python example1.py   # probability selection demo (~1 min)
   ```
   Or `source env/bin/activate` first, then `python main.py`.

To use a different host or model name: `ClefFlash(base_url="http://host:1234/v1", model="...")`.

## Files

- `clef_mlx.py`: `ClefFlash` client with `chat()` and `stream()`. clef-flash often
  puts its answer in `reasoning_content`, so `chat()` returns reasoning + content.
- `main.py`: one plain call and one streamed call.
- `example1.py`: probability selection for support-ticket routing.

## example1: probability selection

`ProbabilitySelector` asks the model for a percentage per option and normalises it.
`Router` routes automatically only when the top option has at least 70% and a margin
of at least 0.25 over the runner-up; otherwise the ticket goes to human review. If the
model reasons past its 400-token budget without giving numbers, it raises `Undecided`,
which also goes to human review.

LM Studio returns no token logprobs for this model, so the percentages are the model's
own stated estimates, not computed probabilities.

```
$ env/bin/python example1.py
> I was charged twice for my Pro plan this month. Please refund the duplicate.
    billing          100.0% ####################
    margin=1.00 entropy=0.00 (4.6s)
    => auto -> billing

> Production dashboard returns 502 for 10 minutes, 300 users blocked!!
    technical        100.0% ####################
    margin=1.00 entropy=0.00 (2.3s)
    => auto -> technical

> Do you offer nonprofit discounts? We'd need about 40 seats.
    sales            100.0% ####################
    margin=1.00 entropy=0.00 (2.1s)
    => auto -> sales

> Got a password reset I didn't request and a login from another country.
    account-security 100.0% ####################
    margin=1.00 entropy=0.00 (1.2s)
    => auto -> account-security

> CONGRATULATIONS you won a free iPhone click here bit.ly/xyz
    spam             100.0% ####################
    margin=1.00 entropy=0.00 (1.3s)
    => auto -> spam

> Upgraded to Enterprise but SSO still not working and the invoice looks wrong too.
    => HUMAN REVIEW (model undecided: 13.2s, no distribution in: 'This is a complex issue involving both billing (invoice wrong) and technical (SSO not working). However, since the custo'…)

> hey quick question about my account
    account-security  60.0% ############
    sales             20.0% ####
    billing           10.0% ##
    technical         10.0% ##
    margin=0.40 entropy=0.68 (6.6s)
    => HUMAN REVIEW (account-security vs sales)
```

Clear tickets get one option at 100% and are routed automatically. The vague ticket
gets a spread distribution and goes to human review, which a single-label classifier
would not flag. The mixed SSO-and-invoice ticket never gets a distribution, which is
also a useful ambiguity signal.
