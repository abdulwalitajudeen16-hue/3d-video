// Reference sheet: turnaround, 10 expressions, 18 mouth shapes. Re-render after any change to LOOK in engine/mentor2d.js.
import { registerShot } from "/engine/core.js";
import { drawCharacterSheet } from "/engine/mentor2d.js";
registerShot("sheet", { draw(g, t, info) { drawCharacterSheet(g, 1920, 1080, t); } });
