# Stroke biomechanics checkpoints (video + pose-metric reading guide)

Use this while viewing burst sheets and annotated pose frames. Every checkpoint is
something visible in 2D footage; pose metrics from `pose/pose_metrics.json` give
numeric corroboration where noted. These are image-plane proxies, not lab
biomechanics — treat borderline numbers as hypotheses to confirm visually.

## Reading pose_metrics.json

| Field | Meaning | Interpretation hints |
|---|---|---|
| `deepest_knee_angle` | min hip–knee–ankle angle in a burst | serve/groundstroke leg loading. ~180 = no bend; 130–150 = decent load; <120 = deep drive. On serves, >160 usually means arm-only serving |
| `max_shoulder_hip_sep_deg` | max angle between shoulder line and hip line | X-factor proxy. <15° = arm swing; 20–40° = real coil. Camera angle inflates/deflates this — confirm visually |
| `mean_stance_width_ratio` | ankle spread / shoulder width | <1.0 = narrow/upright; 1.3–1.8 = athletic base; >2.2 sustained = lunging or stretched |
| `wrist_above_head_frac`, `likely_overhead_action` | fraction of burst frames with a wrist above the nose | identifies serve/overhead bursts; use those bursts for serve scoring |
| `hip_vertical_oscillation` | std of normalized hip height | rhythm proxy: near 0 = flat-footed play, no split step or leg drive; very high = jumping/off-balance |
| `faster_wrist` / `handedness_guess` | which wrist travels faster | sanity-check handedness before writing the report |
| `trunk_lean_deg` | trunk angle from vertical | chronic >25° on neutral balls = balance problem, contact too close/late |

## Serve

1. **Stance & rhythm** — platform or pinpoint; a repeatable count. Toss arm extends fully; toss lands ~arm's length into the court, minimal chase-steps.
2. **Trophy position** — both arms up, hitting elbow ~shoulder height, racquet edge-on; shoulders tilted (front shoulder down). Flat trophy + high elbow droop is the #1 rec-level flaw.
3. **Leg drive** — knees flex then extend up-into contact (`deepest_knee_angle` during overhead bursts). No bend → "arm serve", capped pace and injury-prone.
4. **Racquet drop** — racquet falls behind the back as legs fire (elbow angle closing then whipping open). Abbreviated drop = pushy motion.
5. **Contact & pronation** — full extension (contact near apex, arm straight), forearm pronates through the ball; landing balanced inside the court on the front leg.
6. **Second serve** — is there a distinct spin motion (more shoulder-over-shoulder, contact more behind head), or just a slower push? Push = tactically fragile.

## Forehand

1. **Grip family** (infer from finish + contact height comfort): continental (flat, blocks high balls), eastern (classic, versatile), semi-western (topspin, modern), full western (grinder, struggles low).
2. **Unit turn** — shoulders + hips rotate together early, non-hitting hand on the throat then tracking the ball; watch `max_shoulder_hip_sep_deg`.
3. **Spacing & footwork to the ball** — adjusting steps before the hit; contact ~arm+racquet length away, waist-ish height, IN FRONT of the front hip.
4. **Kinetic chain** — legs → hips → torso → arm sequencing; visible ground push (knee angle closing then opening).
5. **Extension & finish** — hitting through the ball toward the target before wrapping; finish varies with intent (over shoulder = drive, over head "buggy-whip" = defensive/angle) — variety is a sign of skill.
6. **Red flags** — backswing bigger than preparation time allows, contact beside/behind body, open racquet face floaters, falling backward at contact.

## Backhand (one-handed / two-handed)

- **Both**: full shoulder turn (back almost to the net at prep), contact in front, head still.
- **Two-handed**: non-dominant arm drives; hips clear; check high-ball handling and short-angle ability.
- **One-handed**: needs earlier contact; watch balance leg-kick counterweight; slice as a genuine second option (knifed through, not floated).
- **Slice** — is it a controlled skidding ball (shoulder-high to low path, firm wrist) or a defensive float?

## Return of serve

- Ready position lower than rally stance; split step lands AS the server hits.
- vs first serve: compact block/redirect. vs second serve: does the player step in and take charge? Passive deep-court second-serve returns cap the tactics score.

## Net game

- **Approach trigger** — comes in behind short balls/strong approaches, or only when forced?
- **Volley** — punch from the shoulder, firm wrist, minimal backswing; split step before opponent's pass attempt; first volley depth. Swinging volleys on everything = comfort gap.
- **Overhead** — turns sideways immediately, shuffles under the lob, scissor-kick if needed.

## Movement & footwork (score with Tier-2 numbers when available)

- **Split step** — present before EVERY opponent hit (rally + return + at net)? Timing > height. Absence is the single most level-defining habit.
- **First step & recovery** — explosive first step toward the ball; crossover or shuffle recovery toward the correct bisector (not always center mark).
- **Balance at contact** — head still, no falling away on neutral balls.
- From `match_metrics.json`: `distance_m` and `avg_moving_speed_ms` (engagement),
  `mean_dist_behind_baseline_m` (court position identity), `net_approach_frac`
  (style evidence). Ignore fields flagged `suspect`.

## Common fault → drill mapping (feed the development plan)

| Fault seen | Prescription |
|---|---|
| No split step | shadow split-step metronome vs. wall; coach calls "hit" cue |
| Arm-only serve | knee-bend-freeze trophy drill; serve from kneeling→standing progression; throw drills |
| Late contact / cramped spacing | drop-feed contact-in-front drill; "catch it with the left hand" spacing cue |
| No unit turn | medicine-ball rotational throws; shadow swings holding racquet throat |
| Floaty second serve | continental-grip spin serves from service line, progress back |
| Backhand breakdown under pace | wall rally tempo ladder; cross-court-only sets to 11 |
| Passive return position | return from inside baseline on second serves; call target before serve |
| Poor recovery | figure-8 baseline movement drill; recovery-to-bisector cone drill |
