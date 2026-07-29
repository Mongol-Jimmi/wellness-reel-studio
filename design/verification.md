# Prototype Verification

- Five identity clips rendered successfully at 540×960, 30 fps, 150 frames, and exactly 5.000 seconds each.
- Comparison render: H.264/AAC, 540×960, 30 fps, 750 video frames, exactly 25.000 seconds.
- Audio: AAC mono, 48 kHz; comparison measured −20.5 LUFS integrated and −6.8 dBFS true peak.
- Automated black-frame scan: zero black intervals across all six MP4 files.
- Automated tests: 7 passing, covering selection integrity, durations, representative timeline frames, primary/accent contrast, MP4 dimensions/frame counts, audio sample rate, and comparison A/V duration equality.
- Bundled font and licence: `assets/fonts/UbuntuSans.ttf`, `assets/fonts/UBUNTU-FONT-LICENSE.txt`.
- Independent ECC review found no CRITICAL/HIGH issues. Its two MEDIUM findings—aggregate A/V duration mismatch and host-specific font dependency—were fixed and reverified.
- Independent wellness/accessibility review found no blockers. Inner Weather’s dial remains a subjective user-testing question because it could be interpreted as an emotional assessment meter.
- Human creative review at normal playback speed remains required before selecting a master identity.

## Research integration

- Elicit paper search is offline by default; live use requires both `--live` and `--confirm-quota` plus `ELICIT_API_KEY`.
- Default live scope is six requests; topics are deduplicated and capped at ten requests.
- Generated files are explicitly named `candidate-evidence-cards.*` and remain `human_review_required`.
- The client rejects redirects, oversized/malformed responses, retracted-paper searches, hostile/non-HTTPS URLs, raw-HTML title injection, and invalid numeric fields.
- Secure random temporary files prevent symlink-following output writes.
- Final independent security review: **APPROVE**, no remaining CRITICAL/HIGH/MEDIUM findings.
- Live Elicit run completed with explicit quota confirmation: six requests returned 48 records, reduced to 47 unique paper leads after DOI/title deduplication.
- Full suite after live output processing: 23 tests passing; Ruff passing.

External media spend remains USD $0. Elicit plan quota was consumed; check the Elicit account dashboard for any plan-specific credit or monetary impact.
