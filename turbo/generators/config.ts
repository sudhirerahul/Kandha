// config.ts — Turborepo generator for scaffolding new @kandha/* packages
import type { PlopTypes } from "@turbo/gen";

export default function generator(plop: PlopTypes.NodePlopAPI): void {
  plop.setGenerator("package", {
    description: "Create a new @kandha/* shared package",
    prompts: [
      {
        type: "input",
        name: "name",
        message: "Package name (without @kandha/ prefix):",
        validate: (input: string) =>
          /^[a-z][a-z0-9-]*$/.test(input) || "Use lowercase letters, numbers, and hyphens only",
      },
      {
        type: "input",
        name: "description",
        message: "One-line description of the package:",
      },
    ],
    actions: [
      {
        type: "add",
        path: "{{ turbo.paths.root }}/packages/{{ name }}/package.json",
        templateFile: "templates/package.json.hbs",
      },
      {
        type: "add",
        path: "{{ turbo.paths.root }}/packages/{{ name }}/tsconfig.json",
        templateFile: "templates/tsconfig.json.hbs",
      },
      {
        type: "add",
        path: "{{ turbo.paths.root }}/packages/{{ name }}/src/index.ts",
        templateFile: "templates/index.ts.hbs",
      },
    ],
  });
}
