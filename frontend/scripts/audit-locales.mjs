import fs from "node:fs";
import path from "node:path";
import { parse } from "@babel/parser";

const root = path.resolve("src");
const languages = ["en", "it", "es", "fr", "de", "pt"];
const files = languages.map((language) => path.join(root, "locales", language, "translation.json"));
const errors = [];
const empty = [];
const encodingIssues = [];
const usedKeys = new Set();
const hasCorruptEncoding = (text) => [...text].some((char, index, chars) => char === "?"
  && ((/\p{L}/u.test(chars[index - 1] || "") && /\p{L}/u.test(chars[index + 1] || ""))
    || (/\s/.test(chars[index - 1] || "") && /\s/.test(chars[index + 1] || "")
      && /\p{Ll}/u.test(chars[index + 2] || ""))))
  || /(?:\u00c3[\u0080-\u00bf]|\u00c2[\u0080-\u00bf]|\u00e2[\u0080-\u00bf]|\ufffd)/u.test(text);
const flatten = (value, prefix = "") => Object.entries(value).flatMap(([key, child]) => {
  const name = prefix ? `${prefix}.${key}` : key;
  if (child && typeof child === "object") return flatten(child, name);
  if (typeof child === "string" && hasCorruptEncoding(child)) {
    encodingIssues.push(`${name}: ${child}`);
  }
  if (typeof child !== "string" || !child.trim()) empty.push(name);
  return [name];
});

const keysets = files.map((file, index) => {
  try {
    const data = JSON.parse(fs.readFileSync(file, "utf8"));
    return { language: languages[index], keys: flatten(data), data };
  } catch (error) {
    errors.push(`${languages[index]}: invalid JSON (${error.message})`);
    return { language: languages[index], keys: [], data: {} };
  }
});
const english = new Set(keysets[0].keys);
for (const { language, keys } of keysets.slice(1)) {
  const current = new Set(keys);
  const missing = [...english].filter((key) => !current.has(key));
  const extra = [...current].filter((key) => !english.has(key));
  if (missing.length || extra.length) errors.push(`${language}: ${missing.length} missing, ${extra.length} extra keys`);
}

const hardcoded = [];
// Brand terms and the standard document-format abbreviation are intentionally
// shared across locales, so they are not translation omissions.
const intentionallyUntranslated = new Set(["RAFIKI", "CAR HIRE", "PDF"]);
const shouldAuditText = (value) => /\p{L}{3}/u.test(value)
  && !intentionallyUntranslated.has(value.replace(/[.:]/g, "").trim());
const visit = (directory) => {
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const file = path.join(directory, entry.name);
    if (entry.isDirectory()) visit(file);
    else if (/\.(jsx|js)$/.test(entry.name) && !file.includes(`${path.sep}admin${path.sep}`)) {
      let ast;
      try { ast = parse(fs.readFileSync(file, "utf8"), { sourceType: "module", plugins: ["jsx"] }); }
      catch (error) { errors.push(`${path.relative(root, file)}: parse error (${error.message})`); continue; }
      const scan = (node) => {
        if (!node || typeof node !== "object") return;
        if (node.type === "CallExpression"
          && (node.callee?.name === "t" || node.callee?.property?.name === "t")
          && node.arguments?.[0]?.type === "StringLiteral") {
          usedKeys.add(node.arguments[0].value);
        }
        if (node.type === "JSXText") {
          const text = node.value.replace(/\s+/g, " ").trim();
          if (shouldAuditText(text)) hardcoded.push(`${path.relative(root, file)}:${node.loc.start.line}: ${text.slice(0, 100)}`);
        }
        if (node.type === "JSXAttribute" && ["aria-label", "title", "placeholder", "alt", "label"].includes(node.name?.name)
          && node.value?.type === "StringLiteral" && shouldAuditText(node.value.value)) {
          hardcoded.push(`${path.relative(root, file)}:${node.loc.start.line}: ${node.name.name}="${node.value.value}"`);
        }
        for (const [key, value] of Object.entries(node)) {
          if (["loc", "start", "end", "comments", "tokens"].includes(key)) continue;
          if (Array.isArray(value)) value.forEach(scan);
          else if (value && typeof value === "object") scan(value);
        }
      };
      scan(ast);
    }
  }
};
visit(path.join(root, "pages", "public"));
visit(path.join(root, "components"));
const englishKeys = new Set(keysets[0].keys);
const missingUsedKeys = [...usedKeys].filter((key) => !englishKeys.has(key)
  && !englishKeys.has(`${key}_one`) && !englishKeys.has(`${key}_other`));
if (missingUsedKeys.length) errors.push(`${missingUsedKeys.length} used translation keys are missing from English: ${missingUsedKeys.join(", ")}`);

console.log(`Translation keys in English: ${keysets[0].keys.length}`);
console.log(`Static translation keys referenced in public UI: ${usedKeys.size}`);
console.log(`Referenced keys missing from English (excluding dynamic keys): ${missingUsedKeys.length}`);
for (const { language, keys } of keysets) console.log(`${language}: ${keys.length} keys`);
console.log(`Missing or empty values: ${empty.length}`);
console.log(`Possible lost accented characters (letter?letter): ${encodingIssues.length}`);
console.log(`Invalid JSON or key parity errors: ${errors.length}`);
console.log(`Hardcoded customer-facing JSX text candidates: ${hardcoded.length}`);
for (const issue of errors) console.log(`ERROR ${issue}`);
for (const issue of encodingIssues.slice(0, 12)) console.log(`ENCODING ${issue}`);
if (encodingIssues.length > 12) console.log(`ENCODING ... ${encodingIssues.length - 12} more`);
for (const candidate of hardcoded) console.log(`STRING ${candidate}`);
if (empty.length || errors.length || encodingIssues.length || hardcoded.length) process.exitCode = 1;
