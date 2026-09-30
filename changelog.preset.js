'use strict'
// Custom preset for .github/workflows/changelog.yml (TriPSs/conventional-changelog-action's
// `config-file-path` input). The action's built-in "angular"/"conventionalcommits" presets
// only surface feat/fix/perf/revert commits by default - everything else (docs, chore, ci,
// and critically `test`/`tests`, which is most of what this repo's history actually is per
// AGENTS.md) gets silently dropped. This extends the preset so every type allowed by
// .github/workflows/pr-conventions.yml gets its own changelog section.
//
// Pinned to conventional-changelog-conventionalcommits@4, the version the action's own
// bundled conventional-changelog@3.1.24 was built against - newer majors (9+) use a
// different parser/writer schema and fail at render time ("Missing helper").
const config = require('conventional-changelog-conventionalcommits')

module.exports = config({
  types: [
    { type: 'feat', section: 'Features' },
    { type: 'fix', section: 'Bug Fixes' },
    { type: 'perf', section: 'Performance' },
    { type: 'revert', section: 'Reverts' },
    { type: 'docs', section: 'Documentation' },
    { type: 'doc', section: 'Documentation' },
    { type: 'style', section: 'Styling' },
    { type: 'refactor', section: 'Refactor' },
    { type: 'test', section: 'Tests' },
    { type: 'tests', section: 'Tests' },
    { type: 'build', section: 'Build System' },
    { type: 'ci', section: 'Continuous Integration' },
    { type: 'chore', section: 'Chores' },
    { type: 'dev', section: 'Chores' },
  ],
})
