# Query workflow

Plain-English recipe for what happens when a user asks a question.

1. User types (or speaks, transcribed locally via Whisper) a question in the Streamlit chat UI,
   which posts it to the backend along with a `session_id` (created on the first turn), how many
   papers to show, and any source/publication-year filters set in the sidebar.
2. The agent first decides what kind of question this is:
   - About the agent itself ("who are you", "what can you do") → answered directly from a static
     description of the project's goal and capabilities. No search, no papers.
   - Off-topic (unrelated to Alzheimer's/dementia/MCI/neurocognitive research) → a fixed apology
     and redirect message, with example on-topic questions suggested. No LLM call at all for this
     path — nothing to ground, so a static response is both fastest and most reliable.
   - A real research question → continues to the steps below.
3. If this is the first message of a new conversation (and the question is on-topic), the agent
   kicks off a full live literature search scoped to this question's topic in the background,
   adding anything new to the corpus so future answers reflect papers published up to today. This
   does not delay the current answer — it runs concurrently while the steps below proceed against
   whatever's already in the corpus. Later messages in the same conversation skip starting a new
   one.
4. The agent embeds the question and searches the vector store for the most similar chunks
   (respecting any source/year filters), then filters/ranks them (capping how many chunks come
   from the same paper, so one paper can't dominate the evidence).
5. If nothing relevant was found, the agent says so plainly instead of making something up.
6. Otherwise, the agent asks the LLM to write a plain-language, evidence-grounded summary citing
   only the retrieved chunks it actually used, and to suggest 2-4 follow-up questions — both in
   the same call, to keep things fast.
7. The agent then checks, in code, that every citation the LLM produced actually points to a
   chunk it was given (and separately strips any raw internal ID the model might have leaked into
   the summary text itself). If a citation is invalid, it asks the LLM to try again with a
   correction; if it still gets it wrong, the bad citation is silently removed rather than shown
   to the user.
8. The final answer is assembled: a plain-language summary, the list of most relevant papers
   (each with full metadata and links, and an Open Access / Abstract-only badge), and — only if
   the user asked for an opinion — a clearly labeled personal interpretation section. The user can
   click "🔊 Listen" to have the summary read aloud (via the browser, no server-side TTS).
9. The agent closes the turn with a confirmation check ("did this answer your question?") and
   2-4 suggested follow-up questions, so the user can either confirm, ask something else
   entirely, or click a suggestion to keep going.
10. The user can click "Show more papers" to re-run the same question against a larger paper
    count.

The agent always answers directly — there is no pre-answer clarification gate. Earlier
milestone-1 versions asked a clarifying question before searching when a question looked
ambiguous; user feedback was that this got in the way, so the agent now always attempts an
answer and lets the post-answer confirmation + suggestions (and, for meta/off-topic questions,
the intent classification in step 2) handle steering instead.
