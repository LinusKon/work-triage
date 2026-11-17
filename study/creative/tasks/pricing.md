# Brief: pricing page for Relay

Design and build the pricing page for Relay, a tool that replaces a team's daily stand-up with short written
updates. The reader is a team lead comparing three or four tools in one sitting. The page should make the choice
between the plans obvious in a few seconds and make the middle plan the natural pick without shouting. Use the
copy below exactly; the design is yours.

Copy (use every line verbatim, add no other visible text):
- Brand: `Relay`
- Headline: `One update a day. No meeting.`
- Subline: `Pick a plan now, change it any time.`
- Plan 1: `Starter` / `$0` / `per person, per month` / `For teams trying it out` / `Up to 5 people` / `30 days of history` / `One workspace` / Button: `Start free`
- Plan 2: `Team` / `$6` / `per person, per month` / `For teams that run on it` / `Unlimited people` / `Unlimited history` / `Slack and calendar sync` / `Weekly summary by email` / Button: `Try Team for 14 days`
- Plan 3: `Company` / `$14` / `per person, per month` / `For several teams` / `Everything in Team` / `Single sign-on` / `Audit log` / `Priority support` / Button: `Talk to us`
- Label on plan 2: `Most teams pick this`
- Note: `Prices in US dollars. Billed monthly.`
- Footer: `Relay Labs, Lisbon`

Hard requirements:
- One file, `index.html`, in the repository root. Everything is inside it: no other files, no network requests,
  no photo or font files. Illustrations in CSS or inline SVG are allowed.
- Every line of the copy appears exactly as written; no other visible text. (`per person, per month` appears once
  per plan.)
- The page works at 1440 and at 390 CSS pixels width with no horizontal scrolling.
- All three buttons are real `<a>` or `<button>` elements. At 1440 width all three plans and their buttons are
  visible without scrolling (window height 900).
- No errors in the browser console.
