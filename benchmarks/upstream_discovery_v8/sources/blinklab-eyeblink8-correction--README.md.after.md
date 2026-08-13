# blinklab

[![CI](https://github.com/heshipstech/blinklab/actions/workflows/ci.yml/badge.svg)](https://github.com/heshipstech/blinklab/actions/workflows/ci.yml)

A browser based eye signal laboratory. It reads your webcam locally. It turns what your eyes are doing into numbers you can audit: blinks, eyelid aperture in millimetres, gaze regions, fixations, PERCLOS (the share of a minute your eyes spend closed), and an explainable alertness score.

> **Demo, not a safety or medical device. This is a learning project. It is not for clinical, workplace or safety use, its numbers are not diagnostic, and it has not been validated against any medical standard. All processing happens in your browser and no data leaves your device.**

**Live demo: https://heshipstech.github.io/blinklab/**. It is republished automatically on every merge to main. You need a webcam and a browser that allows camera access.

## What it measures

Every number on screen comes from a tested pure function, and every threshold is calibrated against measured data rather than copied from a paper.

- **Blinks**: count, rate per minute, closed-phase duration, closing velocity and the amplitude over velocity ratio.
- **Eyelid aperture in millimetres**, normalised by the iris as a physical ruler, so the reading survives moving closer to or further from the camera.
- **Gaze**: iris offset per eye, screen quadrant, on screen versus off, nine point calibration, fixations and saccades, a dwell heatmap and a scanpath replay.
- **PERCLOS**, the eyes closed share of the last minute, and a long closure detector with a debounced alert.
- **An alertness score, 0 to 100**, that shows its working: it is exactly 100 minus four named penalties, and a panel names the ones that cost you points.
- **A CSV export** (comma separated values, a file a spreadsheet can open) of one record per second, plus a Karolinska Sleepiness Scale self report, for offline analysis.
- **A recorded clip**, not only a live camera. Upload a video file and it runs through exactly the same pipeline, timed by the clip's own clock rather than the wall clock, so the measurements mean the same thing either way.

## Honest limitations

This project's rule is that a limitation you know about belongs in the open.

- Thresholds are personal and learned per session. They are priced against **one** person's measured eyes so far, so another face may need different ones.
- Strong prescription glasses compress and distort the gaze signal near the edges of the screen, so calibrated gaze is reliable in the middle and degrades at the corners.
- The instrument reads fully shut eyes as roughly a third of the open baseline rather than zero, so the literature's usual PERCLOS threshold does not transfer and ours is adjusted to the instrument. This is documented rather than hidden.
- Known open defects live in the [issue tracker](https://github.com/heshipstech/blinklab/issues), including one where an unusually high learned baseline inflates blink durations.
- Self reported sleepiness is a noisy label, and there is no objective validation of the score yet. Earning that is what Phase 7 is for.
- An uploaded clip can be measured two ways and the file records which. Stepped is the default. It seeks to every frame in turn and waits for the measurement. So which frames it measures depends on the recording, not on your computer. It still does not give exactly the same answer twice. The section below on the Eyeblink8 clips says by how much. Watched plays in real time and is capped by how fast the model runs. So a fast clip loses frames, and how many depends on what else your machine is doing. Watching is offered because stepping is slow and unpleasant to film. Every export states its mode, the frames measured and the resulting rate. The app also reports the rate it detected, so you can check it against a clip you know.

## Does it find the blinks a human found?

This is the first time anything here has been measured against somebody
else's work. Eyeblink8 is a public set of eight webcam clips, 71,354
frames in total. A person watched all of them and marked every blink by
hand. They marked 408 blinks. This app was given the same clips and had
to find the same blinks.

|              | First answer, wrong | Corrected               |
| ------------ | ------------------- | ----------------------- |
| Blinks found | 284 of 408          | **338 of 408**          |
| Recall       | 69.6%               | **82.8%**               |
| Precision    | 86.3% (45 invented) | **86.4%** (53 invented) |
| F1           | 77.1%               | **84.6%**               |

Recall is the share of the human's blinks that the app found. Precision
is the share of the app's detections that were real. F1 is the two
numbers put together into one. It always sits close to the lower of the
two. So an app cannot look good by staying quiet, and it cannot look
good by firing all the time.

The corrected run invents more blinks, 53 against 45, and does not
score worse on precision. That is because it makes many more detections
in total, so the invented ones are a smaller share of them.

**One caveat about the last digit.** These are one run, not a fixed
value. The same clip measured again on the same computer with the same
build does not give exactly the same answer. Re-measuring one of the
eight clips changed its false alarms from 7 to 9. Carried into the
totals that reads 86.0% precision and 84.4% F1 instead of 86.4% and
84.6%. Recall did not move in any re-run. Read the last digit of
precision and F1 as approximate, and read recall as solid.

There are two columns because the first answer was wrong. It was wrong
because of a defect in this app. The clips were not the cause. The
first write up of this result was never published on this page. Both
numbers stay here. A project that shows you only its final answer tells
you less than one that also shows you its wrong turn.

**The defect, in plain English.** The app keeps a list of the blinks it
has found, and that one list was doing two jobs. It was the list you
read on screen. To keep the panel short, it held only the newest fifty
detections. It was also the record written into the exported file. So
trimming for the reader trimmed the measurement. Two of the eight clips
hold more than fifty blinks, 88 in one and 72 in the other. In both, the
opening stretch of blinks was deleted before the file was written.
Nothing announced it. The score then said the app had missed those
blinks. It had not missed them. It found them, then threw them away.
There are two lists now. One is for the screen and one is for the
record. The exported file also counts its own rows and compares them
against the number of blinks the app found. If any are missing, it
prints a warning on the first line. Fixed in pull request #172.

**The corrected number is honest, and it is still not good enough.** It
misses roughly one blink in six. Other published detectors are measured
on these same clips. They report F1 in the low nineties. This one is
closer to them than it was. It has not caught them.

Per clip recall now runs from 67.7% to 91.7%. The whole gain sits in the
two clips the defect had cut short. One moved from 55.7% to 89.8% and
the other from 58.3% to 91.7%. That is 30 blinks recovered in one and 24
in the other, 54 in total, which is the entire move from 284 to 338.
Every other clip found exactly the same number of blinks in both runs.

**One caveat about comparing the two runs.** They were built from
different commits, so they are not the same measurement with a single
line changed. Four of the six shorter clips shifted the edges of a blink
by a frame or two, or split one detection into two. The other two report
exactly the same blink timings. One correction to the story above. The
cap counted detections, not the human's blinks. A third clip made
exactly fifty detections and lost its opening one too. That one was a
false alarm, so it changes no recall figure on this page. What the
defect explains is the recall, exactly and entirely: 30 recovered blinks
in one clip, 24 in the other, and not one anywhere else. Fixing it also
surfaced 8 more invented blinks, 45 to 53, and seven of those are in the
two recovered clips.

The clips were checked, frame by frame, before any of this was blamed on
them. The recordings freeze here and there and lose frames. Every clip
ships a `.txt` file listing the time of each frame it kept, so anyone
can count the losses. Here is the rule used. At 30 frames per second one
frame lasts 0.033 seconds. Round each gap between two kept frames to a
whole number of frame lengths. Anything above one is a lost frame. Under
that rule the eight clips lose 787 frames between them, spread over 174
gaps. That is 1.1% of every frame in the set. Twelve of those gaps are
long freezes of half a second or more. Those twelve sit in three clips
and hold 611 of the 787 lost frames. Very few gaps land inside a blink.
At the very most the lost frames explain 4 of the 70 remaining misses.
The script that counts all of this is
[analysis/tools/audit_frame_loss.py](analysis/tools/audit_frame_loss.py),
so you do not have to take the number on trust. Three more checks came
back clean. In all eight clips the person faces the camera in every
single frame. No blink the human marked is shorter than 4 frames, so
none of them are too quick to catch.
Shrinking the video to a quarter of its size changed how strong a blink
looks by 2.7%, so the picture is not too small either. The clips are not
the excuse.

**A claim from the first write up is withdrawn.** One of the eight clips
shows a person wearing glasses. The first write up said that clip scored
83.7% recall, against 67.9% for the seven clips without glasses. It read
that as evidence against this project's own warning about prescription
lenses. That gap was not real. The defect created it. Both of the cut
short clips were in the group without glasses, so that group's score was
pulled down. On the corrected run the glasses clip scores 83.7% recall
and 83.7% precision. The seven without score 82.7% recall and 86.8%
precision. So recall is one point apart, and precision is three points
apart in the other direction. Both figures rest on a single clip of 43
blinks, and both settle nothing in either direction. So the claim is
withdrawn rather than reversed. This project has no evidence yet about
what glasses do to blink detection.

There is a version of this result that reads better, and it is not
printed here. Leave out the blinks the human marked as long closures and
recall rises. Leave out the partial blinks as well and it rises again.
Carry the same reasoning one step further and it rises further still, by
leaving out the blinks the detector missed. Every step sounds defensible
on its own. That last step shows where this reasoning ends up, and it is
plainly cheating. So none of those numbers are on this page, including
the two a reader might have accepted.

**The misses have a pattern.** 55 of the 70 missed blinks, 78.6%,
contain at least one frame the human marked as fully closed. These are
not faint or borderline blinks. They are ordinary ones where this app's
eyelid measurement did not dip far enough to count. That is a real
weakness. Finding out why is the next question.

**The invented blinks have a pattern too.** 45 of the 53 land on top of
a real blink rather than on an open eye, and half of them are 3 frames
long or shorter. That is one blink counted twice, not a blink imagined
from nothing. A refractory period, a short window after a blink in which
a second one cannot be reported, should remove most of them. It is
planned and it is not built.

The rules for what counts as a correct detection were written down
before any result was seen. They are in
`analysis/blinklab/blink_match.py`. Each detection can be matched to at
most one real blink. So an app that fired all the time would score
badly, not perfectly. The blinks from all eight clips are added into one
total, instead of averaging each clip's score. So a clip with 30 blinks
counts for less than a clip with 88. Every clip was measured frame by
frame, and the frame counts were checked against the source. The app
measured 71,356 frames against the 71,354 in the human's files. Two
clips gave one frame more than their file lists. Every other clip
matched exactly.

Full output, including the superseded numbers, in
[docs/eyeblink8-result.txt](docs/eyeblink8-result.txt).

## Does it give the same answer twice?

A measuring instrument that answers differently on different computers is
not measuring the thing. So the same 70 second recording was run through
two browser engines on one machine, stepping every frame:

|                     | Chrome     | Safari     |
| ------------------- | ---------- | ---------- |
| Frames measured     | 4,202      | 4,203      |
| Frame rate detected | 59.99      | 60.00      |
| Long closures found | 1          | 1          |
| PERCLOS peak        | 34.3%      | 34.5%      |
| Eyes shut           | 49 to 58 s | 49 to 58 s |

The file contains 4,202 frames. **Blink rate per minute was identical in
both browsers to the last decimal**, across all 71 seconds. That is one
70 second clip and it is not the whole story. On the eight clips above
the app does not repeat itself exactly from one run to the next. See the
caveat about the last digit. Eyelid aperture differed by 0.02 mm on
average and the learned personal baseline by 0.4 percent, which is what
sampling a frame a fraction earlier during a blink costs.

This is worth stating because the first version of stepped measurement
failed it badly, and failed it invisibly. It played the clip and paused
on each frame, which cannot outrun a video advancing in real time, so it
measured 6,655 frames of a 12,626 frame recording and reported "measured
every frame". How many it lost depended on how busy the machine was. The
current version seeks to each frame instead, so it measures every frame
however busy the machine is.

Safari's extra frame was the final one counted twice, which is fixed.

## Privacy

Everything runs in your browser. No video, image or measurement ever leaves your device. There is no backend, no analytics and no telemetry. The CSV export writes a file to your own disk and uploads nothing.

## Status

Phases 0 through 6 are complete: foundations, pixels, landmarks, measurement, blinks, gaze and attention, and the rolling state with the demo score. Phase 7, the honest evaluation track, is under way: a Python analysis folder, a session loader and plots, a licensing gate, and video upload mode so a recorded clip runs through the same pipeline as the live camera. That is 442 unit tests, 7 end to end tests and 61 Python tests plus 2 skipped, all green on every pull request.

**The licensing gate failed, and that is written down rather than hidden.** [DATASETS.md](DATASETS.md) records roughly forty public datasets assessed against four requirements: face video, a real drowsiness label, per-clip subject identity, and a licence a solo maintainer can rely on in a public repository. None clears all four. The failure turned out to be structural: the openly licensed drowsiness data is physiological traces, still images or synthetic renders, while every video corpus carrying a real sleepiness label is behind a signed agreement, an institutional email check, a non-commercial clause, or no licence at all. Face video is personal data, and the anonymisation that would let a team release it freely is exactly what destroys the per-subject identity a leave one subject out split needs.

So the evaluation track was replanned rather than abandoned. The next result is blink detection measured against an openly licensed corpus with ground-truth blink intervals, which is a smaller claim than a drowsiness classifier and one this project can actually defend.

## How to run

You need Node.js 20 or newer.

```
git clone https://github.com/heshipstech/blinklab.git
cd blinklab
npm install
npm run dev
```

Open the local URL that Vite prints, then allow camera access.

`npm test` runs the unit tests. `npm run e2e` runs the end to end tests, which drive the built app in a headless browser with a fake camera; the first run needs `npx playwright install chromium`.

## How this repo works

The project grows one small increment per session, each one branch, one pull request, one push, each with a written note explaining the idea in plain English. The working documents:

- [PROJECT.md](PROJECT.md), what this is and why.
- [SPEC.md](SPEC.md), the technical contract, including the FeatureRecord, score and CSV contracts.
- [ROADMAP.md](ROADMAP.md), the full increment ladder and its accepted amendments.
- [STATE.md](STATE.md), where things stand right now.
- [LEARNING.md](LEARNING.md), one plain English engineering note per increment, including the ones that record a mistake.
- [docs/UI.md](docs/UI.md), every element the page can show, when it appears, and every string it can contain.
- [test/MANUAL.md](test/MANUAL.md), the checks a machine cannot run, because a headless browser has no face.
- [decisions/](decisions/), architecture decision records.

## License

MIT, with a not a medical device notice. See [LICENSE](LICENSE).
