/**
 * Intro sequence data: phases, dialogue, and panel mappings.
 * Separating data from components makes both easier to maintain.
 */

export const PHASES = {
  FUTURE: 0,
  SETUP: 1,
  DROP: 2,
  AWAKENING: 3,
  TIME_FREEZE: 4,
  LESSON: 5,
  RELEASE: 6,
  COMPLETE: 7
};

export const LESSON_STATES = {
  INITIAL: 'lesson_initial',
  LISTENED: 'lesson_listened',
  SUCCESS: 'lesson_success'
};

/**
 * Maps panel IDs from the API to intro phases.
 * Panels can be reused across multiple phases.
 */
export const PANEL_PHASE_ASSIGNMENTS = [
  { id: 'future_1', phases: ['FUTURE'] },
  { id: 'future_2', phases: ['FUTURE'] },
  { id: 'future_3', phases: ['FUTURE'] },
  { id: 'holo_1', phases: ['SETUP'] },
  { id: 'holo_2', phases: ['SETUP'] },
  { id: 'drop_1', phases: ['DROP'] },
  { id: 'drop_2', phases: ['DROP'] },
  { id: 'beach_1', phases: ['AWAKENING'] },
  { id: 'beach_2', phases: ['AWAKENING'] },
  { id: 'beach_3', phases: ['AWAKENING'] },
  { id: 'beach_4', phases: ['AWAKENING'] },
  { id: 'freeze_1', phases: ['TIME_FREEZE'] },
  { id: 'freeze_2', phases: ['LESSON', 'RELEASE'] },
  { id: 'success_1', phases: ['COMPLETE'] },
  { id: 'success_2', phases: ['COMPLETE'] },
];

/**
 * All dialogue content for the intro sequence.
 * Keyed by phase number or lesson state string.
 */
export const DIALOGUE = {
  [PHASES.FUTURE]: [
    { speaker: 'bimbo', text: "You're really doing this, huh?" },
    { speaker: 'player', text: "I want to learn it properly. Not from archives. From living it." },
    { speaker: 'bimbo', text: "Japanese. Dead for what, three hundred years? Everyone uses translators now. No one actually speaks anymore." },
    { speaker: 'bimbo', text: "I could give you instant fluency, you know. Neural download. Five seconds. Done." },
    { speaker: 'bimbo', text: "But you don't want that. And honestly? I'm glad." },
    { speaker: 'bimbo', text: "Because that's not how meaning works. The struggle is the point. Earning something... that's what makes it real." },
    { speaker: 'bimbo', text: "Alright. I've got a scenario. Dangerous. Dramatic. No easy way out. Perfect for you." }
  ],
  [PHASES.SETUP]: [
    { speaker: 'bimbo', text: "Japan, 1600. The Sengoku period. Warlords, samurai, political intrigue." },
    { speaker: 'bimbo', text: "You'll be an Englishman. Shipwrecked. No Japanese, no allies, no idea what's happening." },
    { speaker: 'bimbo', text: "Sound fun?" }
  ],
  [PHASES.DROP]: [
    { speaker: 'bimbo', text: "Alright. Dropping you in." },
    { speaker: 'bimbo', text: "Remember—I can freeze time for you. Use it to think, to practice, to prepare." },
    { speaker: 'bimbo', text: "Good luck." }
  ],
  [PHASES.AWAKENING]: [
    { speaker: 'narration', text: "Your eyes open. Salt water. Splinters. Chaos." },
    { speaker: 'narration', text: "Rough hands drag you to your feet." },
    { speaker: 'samurai', text: "「何者だ！」", sub: "???" },
    { speaker: 'bimbo', text: "Steady. He's asking who you are." },
    { speaker: 'narration', text: "A blade presses against your throat." },
    { speaker: 'samurai', text: "「答えろ！」", sub: "???" }
  ],
  [PHASES.TIME_FREEZE]: [
    { speaker: 'bimbo', text: "There. Bought you some time. Literally." },
    { speaker: 'bimbo', text: "He wants to know who you are. Let me show you what to say." }
  ],
  [PHASES.LESSON]: [
    { speaker: 'bimbo', text: "Tap the phrase. Listen to how it sounds." }
  ],
  [LESSON_STATES.LISTENED]: [
    { speaker: 'bimbo', text: "Hear the rhythm? The softness? Now try it. Say it to me." }
  ],
  [LESSON_STATES.SUCCESS]: [
    { speaker: 'bimbo', text: "That's it. That's the one. See? You're a natural." },
    { speaker: 'bimbo', text: "Now... ready to say it for real?" }
  ],
  [PHASES.RELEASE]: [
    { speaker: 'bimbo', text: "When time flows, speak. I believe in you." }
  ],
  [PHASES.COMPLETE]: [
    { speaker: 'narration', text: "The samurai's eyes widen. The blade lowers." },
    { speaker: 'samurai', text: "「...外国人か」", sub: "A foreigner...?" },
    { speaker: 'bimbo', text: "You're alive. And your Japanese? Not bad for a first try." },
    { speaker: 'bimbo', text: "Welcome to Japan. The hard part starts now." }
  ]
};

/**
 * Get the phase name from phase number
 */
export function getPhaseName(phase) {
  return Object.keys(PHASES).find(key => PHASES[key] === phase) || 'FUTURE';
}

/**
 * Get dialogue for current phase and lesson state
 */
export function getDialogueForPhase(phase, lessonState) {
  if (phase === PHASES.LESSON && lessonState !== LESSON_STATES.INITIAL) {
    return DIALOGUE[lessonState] || [];
  }
  return DIALOGUE[phase] || [];
}
