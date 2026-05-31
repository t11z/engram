import type { components } from "@engram/contract";

type Note = components["schemas"]["Note"];

/**
 * Curated, deliberately harmless sample notes for the static demo. Everyday,
 * neutral topics only — nothing political, personal, or otherwise sensitive.
 * The mock API store ({@link ./api.demo.ts}) seeds itself from these.
 */
export const seedNotes: Note[] = [
  {
    id: "01JADEMO000000000000000001",
    title: "Sourdough starter schedule",
    path: "2026/sourdough-starter-schedule.md",
    tags: ["cooking", "baking"],
    created_at: "2026-01-08T07:30:00Z",
    updated_at: "2026-05-18T07:45:00Z",
    body:
      "# Sourdough starter\n\nKeep the rhythm and it stays happy.\n\n- **Morning** — discard half, feed 1:1:1 (starter : flour : water by weight).\n- **Evening** — same feed, keep at room temperature (~22 °C).\n- Ready to bake when it **doubles in 4–6 hours** and passes the float test.\n\n> Going away? Move it to the fridge and feed once a week.\n",
  },
  {
    id: "01JADEMO000000000000000002",
    title: "Pour-over coffee ratio",
    path: "2026/pour-over-coffee-ratio.md",
    tags: ["coffee"],
    created_at: "2026-02-02T06:10:00Z",
    updated_at: "2026-05-21T06:15:00Z",
    body:
      "# Pour-over\n\nA reliable starting point, then adjust to taste.\n\n- Ratio **1:16** — e.g. 20 g coffee to 320 g water.\n- Grind: **medium**, like coarse sand.\n- Water just off the boil (~94 °C).\n- **Bloom** 30 s with ~40 g water, then pour in slow circles.\n- Total brew time: 2:30–3:00.\n\nToo bitter → grind coarser. Too sour → grind finer.\n",
  },
  {
    id: "01JADEMO000000000000000003",
    title: "Houseplant watering guide",
    path: "2026/houseplant-watering-guide.md",
    tags: ["plants", "home"],
    created_at: "2025-11-14T18:00:00Z",
    updated_at: "2026-04-30T17:20:00Z",
    body:
      "# Watering cheatsheet\n\nWhen in doubt, underwater.\n\n| Plant   | Frequency        | Notes                          |\n| ------- | ---------------- | ------------------------------ |\n| Monstera| ~weekly          | Let top 2–3 cm dry out first.  |\n| Pothos  | every 7–10 days  | Very forgiving; tolerates low light. |\n| ZZ      | every 2–3 weeks  | Stores water; hates soggy soil.|\n\nAlways pour off whatever collects in the saucer.\n",
  },
  {
    id: "01JADEMO000000000000000004",
    title: "Reading list 2026",
    path: "2026/reading-list-2026.md",
    tags: ["reading"],
    created_at: "2026-01-02T20:00:00Z",
    updated_at: "2026-05-12T21:05:00Z",
    body:
      "# Reading list 2026\n\nA mix of fiction and craft.\n\n- [ ] *The Pragmatic Programmer* — Hunt & Thomas\n- [ ] *Moby-Dick* — Herman Melville\n- [x] *The Phoenix Project* — Kim, Behr, Spafford\n- [ ] *A Philosophy of Software Design* — Ousterhout\n- [ ] *Bartleby, the Scrivener* — Melville (short, re-read)\n",
  },
  {
    id: "01JADEMO000000000000000005",
    title: "Weekend hiking checklist",
    path: "2026/weekend-hiking-checklist.md",
    tags: ["outdoors"],
    created_at: "2026-03-20T08:00:00Z",
    updated_at: "2026-05-24T08:10:00Z",
    body:
      "# Day-hike checklist\n\nPack the night before.\n\n- Water (1.5–2 L) and a couple of snacks\n- Map + compass (don't rely on the phone)\n- Rain jacket and a warm layer\n- Sunscreen, hat, small first-aid kit\n- Fully charged phone, power bank\n\n*Tell someone the route and your expected return time.*\n",
  },
  {
    id: "01JADEMO000000000000000006",
    title: "Postgres backup command",
    path: "2026/postgres-backup-command.md",
    tags: ["ops", "postgres"],
    source_url: "https://example.com/postgres-backup",
    created_at: "2026-01-10T09:00:00Z",
    updated_at: "2026-04-10T09:30:00Z",
    body:
      "# Nightly backup\n\nPlain-format dump, compressed:\n\n```bash\npg_dump --no-owner --format=custom \\\n  --file=\"backup-$(date +%F).dump\" mydb\n```\n\nRestore into a fresh database:\n\n```bash\npg_restore --no-owner --dbname=mydb backup-2026-04-10.dump\n```\n",
  },
  {
    id: "01JADEMO000000000000000007",
    title: "Git rebase cheatsheet",
    path: "2026/git-rebase-cheatsheet.md",
    tags: ["dev", "git"],
    created_at: "2025-12-05T11:00:00Z",
    updated_at: "2026-05-06T11:25:00Z",
    body:
      "# Rebase, briefly\n\nTidy history before opening a PR.\n\n```bash\ngit rebase -i main      # squash / reword / reorder\ngit rebase --continue   # after resolving conflicts\ngit rebase --abort      # bail out, nothing lost\n```\n\nRule of thumb: rebase your **own** feature branches; never rewrite shared history.\n",
  },
  {
    id: "01JADEMO000000000000000008",
    title: "Markdown syntax reference",
    path: "2026/markdown-syntax-reference.md",
    tags: ["writing", "reference"],
    created_at: "2025-10-22T15:00:00Z",
    updated_at: "2026-03-28T15:40:00Z",
    body:
      "# Markdown in 60 seconds\n\n## Headings\n\nUse `#` through `######`.\n\n## Emphasis\n\n*italic*, **bold**, `inline code`.\n\n## Lists\n\n1. Ordered\n2. Items\n\n- Unordered\n- Items\n\n## Links & quotes\n\n[A link](https://example.com)\n\n> A blockquote.\n\n```python\nprint(\"and fenced code blocks\")\n```\n",
  },
  {
    id: "01JADEMO000000000000000009",
    title: "Weekly meal prep ideas",
    path: "2026/weekly-meal-prep-ideas.md",
    tags: ["cooking"],
    created_at: "2026-02-18T19:00:00Z",
    updated_at: "2026-05-15T19:30:00Z",
    body:
      "# Meal prep\n\nMake once, eat through the week.\n\n- **Overnight oats** — oats + milk + chia, top with fruit in the morning.\n- **Big pot of soup** — lentil or minestrone, freezes well.\n- **Salad jars** — dressing at the bottom, greens on top, shake before eating.\n- **Roasted veg tray** — whatever's in season, olive oil, herbs.\n",
  },
  {
    id: "01JADEMO000000000000000010",
    title: "Travel packing list",
    path: "2026/travel-packing-list.md",
    tags: ["travel"],
    created_at: "2026-04-01T12:00:00Z",
    updated_at: "2026-05-20T12:45:00Z",
    body:
      "# Carry-on essentials\n\nKeep it to one bag.\n\n- Documents: ID/passport, tickets, a printed copy\n- Chargers + a universal adapter\n- A change of clothes and basic toiletries (travel size)\n- Refillable water bottle (empty through security)\n- Snacks, headphones, a book\n",
  },
  {
    id: "01JADEMO000000000000000011",
    title: "Indoor stretching routine",
    path: "2026/indoor-stretching-routine.md",
    tags: ["health"],
    created_at: "2026-03-09T07:00:00Z",
    updated_at: "2026-05-09T07:15:00Z",
    body:
      "# 10-minute stretch\n\nGentle, every morning. Breathe slowly; never force a stretch.\n\n1. Neck rolls — 1 min\n2. Shoulder circles — 1 min\n3. Standing forward fold — 2 min\n4. Cat–cow — 2 min\n5. Seated twist — 2 min each side\n",
  },
  {
    id: "01JADEMO000000000000000012",
    title: "Project kickoff notes",
    path: "2026/project-kickoff-notes.md",
    tags: ["work", "meeting"],
    created_at: "2026-05-04T13:00:00Z",
    updated_at: "2026-05-28T13:20:00Z",
    body:
      "# Kickoff — notes\n\n## Goals\n\n- Agree on scope for the first milestone\n- Decide how we track work and who reviews what\n\n## Next steps\n\n- [ ] Draft the milestone checklist\n- [ ] Set up a shared board\n- [ ] Schedule a short weekly sync\n\n*Placeholder names omitted — this is a sample note.*\n",
  },
];

/** Soft-deleted notes, shown under Trash and restorable in the demo. */
export const seedTrash: Note[] = [
  {
    id: "01JADEMO0000000000000TRASH1",
    title: "Old draft — packing list (superseded)",
    path: ".trash/2026/old-packing-list.md",
    tags: ["draft"],
    created_at: "2026-01-15T10:00:00Z",
    updated_at: "2026-02-01T10:00:00Z",
    body: "Early packing list, replaced by the cleaner version. Kept here only to show restore.\n",
  },
  {
    id: "01JADEMO0000000000000TRASH2",
    title: "Duplicate coffee note",
    path: ".trash/2026/coffee-dupe.md",
    tags: ["coffee"],
    created_at: "2026-02-03T06:00:00Z",
    updated_at: "2026-02-03T06:05:00Z",
    body: "Accidental duplicate of the pour-over note.\n",
  },
  {
    id: "01JADEMO0000000000000TRASH3",
    title: "Scratch — todo",
    path: ".trash/2026/scratch-todo.md",
    tags: ["draft"],
    created_at: "2025-12-20T09:00:00Z",
    updated_at: "2025-12-21T09:00:00Z",
    body: "- [ ] tidy desk\n- [ ] water plants\n\nA throwaway scratch note.\n",
  },
];
