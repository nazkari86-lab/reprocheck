# blinklab

[![CI](https://github.com/heshipstech/blinklab/actions/workflows/ci.yml/badge.svg)](https://github.com/heshipstech/blinklab/actions/workflows/ci.yml)

A browser based eye signal laboratory. It reads your webcam locally and turns what your eyes are doing into numbers you can audit: blinks, eyelid aperture in millimetres, gaze regions, fixations, PERCLOS, and an explainable alertness score.

> **Demo, not a safety or medical device. This is a learning project. It is not for clinical, workplace or safety use, its numbers are not diagnostic, and it has not been validated against any medical standard. All processing happens in your browser and no data leaves your device.**

**Live demo: https://heshipstech.github.io/blinklab/** — republished automatically on every merge to main. You need a webcam and a browser that allows camera access.

## What it measures

Every number on screen comes from a tested pure function, and every threshold is calibrated against measured data rather than copied from a paper.

- **Blinks**: count, rate per minute, closed-phase duration, closing velocity and the amplitude over velocity ratio.
- **Eyelid aperture in millimetres**, normalised by the iris as a physical ruler, so the reading survives moving closer to or further from the camera.
- **Gaze**: iris offset per eye, screen quadrant, on screen versus off, nine point calibration, fixations and saccades, a dwell heatmap and a scanpath replay.
- **PERCLOS**, the eyes closed share of the last minute, and a long closure detector with a debounced alert.
- **An alertness score, 0 to 100**, that shows its working: it is exactly 100 minus four named penalties, and a panel names the ones that cost you points.
- **A CSV export** of one record per second, plus a Karolinska Sleepiness Scale self report, for offline analysis.
- **A recorded clip**, not only a live camera. Upload a video file and it runs through exactly the same pipeline, timed by the clip's own clock rather than the wall clock, so the measurements mean the same thing either way.

## Honest limitations

This project's rule is that a limitation you know about belongs in the open.

- Thresholds are personal and learned per session. They are priced against **one** person's measured eyes so far, so another face may need different ones.
- Strong prescription glasses compress and distort the gaze signal near the edges of the screen, so calibrated gaze is reliable in the middle and degrades at the corners.
- The instrument reads fully shut eyes as roughly a third of the open baseline rather than zero, so the literature's usual PERCLOS threshold does not transfer and ours is adjusted to the instrument. This is documented rather than hidden.
- Known open defects live in the [issue tracker](https://github.com/heshipstech/blinklab/issues), including one where an unusually high learned baseline inflates blink durations.
- Self reported sleepiness is a noisy label, and there is no objective validation of the score yet. Earning that is what Phase 7 is for.
- An uploaded clip can be measured two ways and the file records which. Stepped, the default, seeks to every frame in turn and waits for the measurement, so the result depends on the recording rather than on your computer. Watched plays in real time and is capped by how fast the model runs, so a fast clip loses frames, and how many depends on what else your machine is doing. Watching is offered because stepping is slow and unpleasant to film. Every export states its mode, the frames measured and the resulting rate, and the app reports the rate it detected so you can check it against a clip you know.

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
both browsers to the last decimal**, across all 71 seconds. Eyelid
aperture differed by 0.02 mm on average and the learned personal
baseline by 0.4 percent, which is what sampling a frame a fraction
earlier during a blink costs.

This is worth stating because the first version of stepped measurement
failed it badly, and failed it invisibly. It played the clip and paused
on each frame, which cannot outrun a video advancing in real time, so it
measured 6,655 frames of a 12,626 frame recording and reported "measured
every frame". How many it lost depended on how busy the machine was. The
current version seeks to each frame instead and does not care.

Safari's extra frame was the final one counted twice, which is fixed.

## Privacy

Everything runs in your browser. No video, image or measurement ever leaves your device. There is no backend, no analytics and no telemetry. The CSV export writes a file to your own disk and uploads nothing.

## Status

Phases 0 through 6 are complete: foundations, pixels, landmarks, measurement, blinks, gaze and attention, and the rolling state with the demo score. Phase 7, the honest evaluation track, is under way: a Python analysis folder, a session loader and plots, a licensing gate, and video upload mode so a recorded clip runs through the same pipeline as the live camera. That is 424 unit tests, 5 end to end tests and 54 Python tests, all green on every pull request.

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
