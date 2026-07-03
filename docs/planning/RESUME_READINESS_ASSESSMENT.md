# Occasionally Divine - Resume Readiness Assessment

Reviewed on: 2026-07-01  
Reviewer stance: candid internship/resume evaluation for a 3rd-year engineering student in India.

## Short Verdict

Yes, this project is worth putting on your resume, but not in its current public repository state.

The idea is strong: a full-stack god-simulator game with FastAPI, React, SQLAlchemy, LLM-generated narrative, and Cognee-backed persistent memory. For a 3rd-year student, that is more interesting than another CRUD app, portfolio site, weather app, or basic ML notebook.

But the repo currently looks unfinished and messy enough that it could hurt you if a recruiter or engineer opens GitHub and inspects it carefully. The project should go on your resume only after a cleanup pass and after fixing the frontend/backend API mismatch.

My honest rating:

| Area | Score | Honest judgment |
|---|---:|---|
| Concept originality | 9/10 | Strong and memorable. This is the project's biggest asset. |
| Technical ambition | 8/10 | Full-stack app plus LLM memory/RAG-style architecture is impressive for your year. |
| Backend depth | 7/10 | Real domain model, services, API routes, simulation logic, Cognee integration. Some rough edges. |
| Frontend quality | 5/10 | Builds, but the UI is behind the backend design and still calls stale endpoints. |
| Product completeness | 4/10 | More prototype than finished app right now. |
| Code hygiene | 3/10 | Tracked `venv`, `__pycache__`, SQLite DB, build artifacts, possible `.env`, and no tests. |
| Resume signal today | 6/10 | Good talking point, risky GitHub link. |
| Resume signal after cleanup | 8/10 | Could be one of your strongest projects. |

## What This Project Signals Well

This project shows you can think beyond tutorials. The strongest signal is that you tried to build a system, not just a page:

- FastAPI backend with multiple route modules.
- SQLAlchemy domain model for kingdom state, elders, situations, events, adaptations, council meetings, rumors, and chronicles.
- React/Vite frontend with a dashboard-style game UI.
- LLM prompt engineering for situations, seasonal epilogues, and council debates.
- Cognee integration for persistent narrative memory across datasets like `kingdom_history`, `elder_history`, `rumor_history`, and `disaster_history`.
- Structured Pydantic memory schemas that convert events into natural-language graph facts.
- Architecture/design docs that show intentional planning.

That is a good internship signal because it gives interviewers multiple hooks: backend design, database modeling, AI integration, product thinking, state management, and tradeoffs in LLM reliability.

## Biggest Resume Risk

The repository currently looks like a local hackathon workspace, not a polished public project.

Observed issues:

- `backend/venv` appears in git status with thousands of files. Never publish a virtual environment in a resume project.
- `__pycache__` files are tracked/staged.
- `backend/occasionally_divine.db` is tracked/staged.
- `frontend/node_modules` exists locally. It may not be tracked, but it should never be committed.
- `frontend/dist` exists locally. For an app repo, avoid committing build output unless there is a specific deployment reason.
- `backend/.env` exists locally. I did not read it, but its presence is a serious warning. Make sure no secrets are committed.
- `.gitignore` already ignores many of these, but they still appear in git status, meaning they were likely added before the ignore rules or are staged/tracked.
- No tests are present.
- The folder name `architecure_docs` is misspelled. Small issue, but visible polish matters.

For Indian internship hiring, many resume screeners will not inspect deeply, but the stronger companies and serious interviewers often do. If they open the repo and see a committed venv, it immediately lowers trust.

## Functional Concerns

The frontend and backend are not fully aligned.

The backend exposes:

- `POST /generate_situation`
- `POST /execute_intervention`
- `POST /trigger_council`
- `POST /resolve_council`
- `GET /world_state`
- `GET /memory`
- `POST /reset`

But the frontend client still calls:

- `POST /player_action`

I did not find a matching backend route for `/player_action`. That means the visible game loop is likely broken or based on an older version of the backend.

This is the most important product issue to fix before putting the GitHub link on your resume. A project can be rough, but it should at least run through its core demo path.

## Verification Performed

Frontend:

- `npm run build` passed.
- `npm run lint` passed with two warnings:
  - unused `onTriggerCouncil` parameter in `CouncilChamber.jsx`
  - unused `adaptation_id` variable in `CouncilChamber.jsx`

Backend:

- `python3 -m compileall backend` completed successfully.
- Caveat: it also walked through `backend/venv`, which reinforces the repo hygiene problem.

Not verified:

- End-to-end gameplay.
- Cognee runtime behavior.
- LLM provider/API-key setup.
- Database migrations.
- Automated tests, because none were found.

## Resume Value By Internship Type

For web/full-stack internships: good, after cleanup. You can present it as a full-stack simulation game using FastAPI, React, SQLAlchemy, and LLM APIs.

For AI/LLM internships: good, if you emphasize persistent memory, graph/RAG-style retrieval, prompt design, and structured memory schemas. You should be ready to explain why Cognee was used and what it adds beyond plain chat completion.

For SDE internships at product companies: decent, but only if you fix repo hygiene and add tests. These companies care less about the theme and more about whether your code is maintainable.

For game-dev internships: interesting concept, but the gameplay is still more narrative dashboard than polished game. Do not oversell it as a finished game.

For elite internships: not enough yet. It needs tests, a clean README, deployment/demo video, and a working end-to-end flow.

## How To Put It On Your Resume

Do not write:

> Built an AI game using React and FastAPI.

That sounds generic.

Better version:

> Built Occasionally Divine, a full-stack AI simulation game where player actions modify a persistent kingdom state and LLM-generated council debates use graph-backed memory of prior events.

Stronger bullet set:

- Built a full-stack narrative simulation game using React, FastAPI, SQLAlchemy, and SQLite/PostgreSQL-compatible persistence.
- Designed a domain model for kingdoms, elders, situations, historical events, adaptations, rumors, and council meetings.
- Integrated Cognee-backed memory retrieval to let future LLM-generated events reference prior decisions and elder stances.
- Created structured Pydantic memory schemas to convert gameplay events into retrievable semantic history.
- Implemented AI-generated crises, intervention choices, seasonal progression, council debate, and adaptation mechanics.

If you have only 2 resume bullets, use:

- Built a full-stack AI strategy game with React, FastAPI, SQLAlchemy, and LLM-generated narrative events driven by persistent game state.
- Integrated Cognee-based semantic memory so council debates and future crises can reference previous player actions, elder stances, and historical consequences.

## What To Fix Before Sharing Publicly

Priority 1:

- Remove `backend/venv` from git tracking.
- Remove all `__pycache__` and `*.pyc` files from tracking.
- Remove `backend/occasionally_divine.db` from tracking.
- Ensure `.env` is not tracked and rotate any exposed keys if it ever was committed.
- Keep `package-lock.json`, but do not commit `node_modules`.

Priority 2:

- Fix the frontend API flow to use `generate_situation` and `execute_intervention`, or add a backend `/player_action` route if that is the intended abstraction.
- Add a root `README.md` with setup commands, environment variables, architecture, screenshots, and a 2-minute demo flow.
- Rename `architecure_docs` to `architecture_docs`.
- Add at least 5 focused backend tests for the simulation/action/council logic.
- Add a short demo video or GIF. For this kind of project, a demo matters more than a deployed URL.

Priority 3:

- Make adaptations mechanically affect future situations, not only appear in prompts.
- Add error handling around LLM/Cognee failures in a way the UI can display.
- Add a `.env.example`.
- Add seed/reset scripts.
- Add API docs or screenshots of Swagger UI.

## Interview Talking Points

Good answers to prepare:

- Why did you use Cognee instead of just storing text in SQL?
- What happens when the LLM returns invalid JSON?
- How do you prevent AI-generated effects from breaking game balance?
- What is stored in SQL versus graph memory?
- How would you test LLM-dependent code?
- What would you improve if this became a real product?
- How would you deploy this safely with API keys?

Your best technical story is:

> I wanted the game to remember not just numeric state, but narrative consequences. SQL stores the current state and short-term structured history, while Cognee stores semantic memory across event datasets. The LLM retrieves that memory to generate future situations and council debates that reference past decisions.

That is a genuinely good story if the repo supports it cleanly.

## Final Judgment

Put it on your resume after cleanup. Right now, I would not attach the GitHub link.

As a private project and interview talking point, it is already strong. As a public resume project, it needs one serious polish pass. The concept is above average. The implementation is ambitious. The repo hygiene is below professional standard. Fixing that gap would make this a strong 3rd-year internship project.

