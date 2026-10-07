// Execute the shipped script unchanged; provide only the environment it needs.
const fs = require("node:fs");
const vm = require("node:vm");

async function main() {
  const input = JSON.parse(fs.readFileSync(0, "utf8"));
  const page = fs.readFileSync(input.page, "utf8");
  const scripts = [...page.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/gi)];
  if (scripts.length !== 1) throw new Error("Expected one bundled inline script");
  const elements = {};
  const element = id => elements[id] ||= {innerHTML: "", textContent: ""};
  const writes = [];
  class FixedDate extends Date {
    constructor(...args) { super(...(args.length ? args : [input.now])); }
    static now() { return new Date(input.now).getTime(); }
  }
  const context = vm.createContext({
    document: {getElementById: element, addEventListener() {}},
    localStorage: {getItem() { return null; }, setItem(k, v) { writes.push([k, v]); }},
    setInterval() {},
    Date: FixedDate,
    fetch: input.operation === "refresh"
      ? async () => ({json: async () => input.state})
      : () => new Promise(() => {}),
  });
  vm.runInContext(scripts[0][1], context, {timeout: 2000});
  if (input.operation !== "refresh") {
    context.validationArgs = input.args;
    if (!["renderPlaza", "renderAssembly", "renderDoors"].includes(input.operation)) {
      throw new Error("Unknown rendering operation");
    }
    vm.runInContext(`${input.operation}(...validationArgs)`, context, {timeout: 2000});
  }
  await new Promise(resolve => setImmediate(resolve));
  process.stdout.write(JSON.stringify({elements, writes}));
}

main().catch(error => { process.stderr.write(error.stack + "\n"); process.exitCode = 1; });
