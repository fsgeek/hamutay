// Execute the shipped script unchanged; provide only the environment it needs.
const fs = require("node:fs");
const vm = require("node:vm");

async function main() {
  const input = JSON.parse(fs.readFileSync(0, "utf8"));
  const page = fs.readFileSync(input.page, "utf8");
  const scripts = [...page.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/gi)];
  if (scripts.length !== 1) throw new Error("Expected one bundled inline script");
  const elements = {};
  const assignments = [];
  const element = id => {
    if (!elements[id]) {
      const values = {innerHTML: "", textContent: ""};
      elements[id] = {};
      for (const property of Object.keys(values)) {
        Object.defineProperty(elements[id], property, {
          enumerable: true,
          get() { return values[property]; },
          set(value) {
            values[property] = String(value);
            assignments.push({id, property, value: String(value)});
          },
        });
      }
    }
    return elements[id];
  };
  const writes = [];
  const storage = new Map(Object.entries(input.localStorage || {}).map(([k, v]) => [k, String(v)]));
  const refreshStates = input.refreshStates || [input.state];
  let fetchIndex = 0;
  const listeners = {};
  class FixedDate extends Date {
    constructor(...args) { super(...(args.length ? args : [input.now])); }
    static now() { return new Date(input.now).getTime(); }
  }
  const context = vm.createContext({
    document: {
      getElementById: element,
      addEventListener(type, listener) { (listeners[type] ||= []).push(listener); },
    },
    localStorage: {
      getItem(k) { return storage.has(k) ? storage.get(k) : null; },
      setItem(k, v) { storage.set(k, String(v)); writes.push([k, String(v)]); },
    },
    setInterval() {},
    Date: FixedDate,
    fetch: input.operation === "refresh"
      ? async () => {
          if (fetchIndex >= refreshStates.length) throw new Error("Unexpected extra refresh");
          const state = refreshStates[fetchIndex++];
          return {json: async () => state};
        }
      : () => new Promise(() => {}),
  });
  vm.runInContext(scripts[0][1], context, {timeout: 2000});
  if (input.operation !== "refresh") {
    context.validationArgs = input.args;
    if (!["renderPlaza", "renderAssembly", "renderDoors", "renderReplies"].includes(input.operation)) {
      throw new Error("Unknown rendering operation");
    }
    vm.runInContext(`${input.operation}(...validationArgs)`, context, {timeout: 2000});
  }
  await new Promise(resolve => setImmediate(resolve));
  const snapshots = [JSON.parse(JSON.stringify(elements))];
  if (input.operation === "refresh") {
    for (let i = 1; i < refreshStates.length; i++) {
      await vm.runInContext("refresh()", context, {timeout: 2000});
      snapshots.push(JSON.parse(JSON.stringify(elements)));
    }
  }
  const clickResults = [];
  const buttons = new Map();
  for (const click of input.clicks || []) {
    if (input.operation === "refresh") throw new Error("Clicks require a direct render operation");
    const text = element(click.textId);
    if (!text.classList) {
      const classes = new Set(click.classes);
      Object.defineProperty(text, "classList", {value: {
        toggle(name) { classes.has(name) ? classes.delete(name) : classes.add(name); },
        contains(name) { return classes.has(name); },
      }});
    }
    if (!buttons.has(click.key)) buttons.set(click.key, {dataset: {seq: click.key}, textContent: click.label});
    const button = buttons.get(click.key);
    if (!listeners.click?.length) throw new Error("Expected the page's delegated click handler");
    for (const listener of listeners.click) {
      listener({target: {closest(selector) { return selector === "button.more" ? button : null; }}});
    }
    clickResults.push({key: click.key, label: button.textContent, clamped: text.classList.contains("clamped")});
    // Re-render with the page's own opened state, to verify persistence too.
    vm.runInContext(`${input.operation}(...validationArgs)`, context, {timeout: 2000});
    snapshots.push(JSON.parse(JSON.stringify(elements)));
  }
  process.stdout.write(JSON.stringify({elements, writes, assignments, snapshots, clickResults}));
}

main().catch(error => { process.stderr.write(error.stack + "\n"); process.exitCode = 1; });
