import { normalizeMermaidSource } from "./mermaid.js";

function formatFields(fields) {
  if (!fields.length) {
    return "- 없음";
  }

  return fields
    .map((field) => {
      const required = field.required ? "required" : "optional";
      return `- \`${field.name}\` (${field.type}, ${required}): ${field.description}`;
    })
    .join("\n");
}

function formatColumns(columns) {
  if (!columns.length) {
    return "- 없음";
  }

  return columns
    .map((column) => {
      const constraints = column.constraints?.join(", ") || "none";
      return `- \`${column.name}\` (${column.type}, ${constraints}): ${column.description}`;
    })
    .join("\n");
}

function formatConsiderations(items) {
  if (!items?.length) {
    return "- 없음";
  }

  return items
    .map((item) => `- **${item.title}** \`${item.priority}\` (${item.category}): ${item.description}`)
    .join("\n");
}

function formatImplementationPlan(steps) {
  if (!steps?.length) {
    return "- 없음";
  }

  return steps
    .map((step) => `- **${step.phase}. ${step.title}**: ${step.description}`)
    .join("\n");
}

export function blueprintToMarkdown(blueprint) {
  const lines = [
    "# DevBlueprint AI Result",
    "",
    "## Overview",
    blueprint.overview,
    "",
    "## Features",
  ];

  blueprint.features.forEach((feature) => {
    lines.push(`- **${feature.name}** \`${feature.priority}\`: ${feature.description}`);
  });

  lines.push(
    "",
    "## Tech Stack",
    `- Backend: ${blueprint.tech_stack.backend.join(", ") || "none"}`,
    `- Frontend: ${blueprint.tech_stack.frontend.join(", ") || "none"}`,
    `- Database: ${blueprint.tech_stack.database.join(", ") || "none"}`,
    `- AI: ${blueprint.tech_stack.ai.join(", ") || "none"}`,
    `- Rationale: ${blueprint.tech_stack.rationale}`,
    "",
    "## API Spec",
  );

  blueprint.api_spec.forEach((endpoint) => {
    lines.push(
      `### ${endpoint.method} ${endpoint.path}`,
      endpoint.description,
      "",
      "#### Request",
      formatFields(endpoint.request),
      "",
      "#### Response",
      formatFields(endpoint.response),
      "",
    );
  });

  lines.push("## Database Schema");
  blueprint.database_schema.forEach((table) => {
    lines.push(`### ${table.name}`, table.description, "", formatColumns(table.columns), "");
  });

  lines.push(
    "## Non-functional Requirements",
    formatConsiderations(blueprint.non_functional_requirements),
    "",
    "## Security Considerations",
    formatConsiderations(blueprint.security_considerations),
    "",
    "## Implementation Plan",
    formatImplementationPlan(blueprint.implementation_plan),
    "",
    "## Database ERD",
    "```mermaid",
    normalizeMermaidSource(blueprint.database_erd),
    "```",
    "",
    "## Sequence Diagram",
    "```mermaid",
    blueprint.sequence_diagram,
    "```",
    "",
  );

  return lines.join("\n");
}

export function buildMarkdownFileName(idea) {
  const normalizedIdea = idea.trim().replace(/\s+/g, " ");
  const safeName = normalizedIdea.replace(/[\\/:*?"<>|]+/g, "").replace(/^[ .]+|[ .]+$/g, "");
  return `${(safeName || "devblueprint-result").slice(0, 80)}.md`;
}

export function downloadMarkdown(idea, blueprint) {
  const blob = new Blob([blueprintToMarkdown(blueprint)], {
    type: "text/markdown;charset=utf-8",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = buildMarkdownFileName(idea);
  link.click();
  URL.revokeObjectURL(url);
}
