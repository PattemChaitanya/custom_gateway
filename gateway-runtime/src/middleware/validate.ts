/**
 * Validation middleware — JSON Schema via ajv.
 * Validates path params, query params, request body, and required headers.
 */

import Ajv from "ajv";
import addFormats from "ajv-formats";
import type { Request, Response, NextFunction } from "express";
import type { GatewayRoute, ParamSchema, HeaderSchema } from "../types.js";

const ajv = new Ajv({ allErrors: true, coerceTypes: true });
addFormats(ajv);

function coerce(value: string, type: ParamSchema["type"]): unknown {
  if (type === "number" || type === "integer") return Number(value);
  if (type === "boolean") return value === "true";
  return value;
}

export function makeValidateMiddleware(route: GatewayRoute) {
  const schema = route.validation_schema;

  return function validate(req: Request, res: Response, next: NextFunction): void {
    if (!schema) {
      next();
      return;
    }

    const errors: { field: string; message: string }[] = [];

    // — Path params —
    if (schema.path_params) {
      for (const [name, rule] of Object.entries(schema.path_params)) {
        const raw = req.params[name];
        if (raw === undefined) {
          if (rule.required !== false) errors.push({ field: `path.${name}`, message: "required" });
          continue;
        }
        const coerced = coerce(raw, rule.type);
        if (rule.pattern && !new RegExp(rule.pattern).test(String(coerced))) {
          errors.push({ field: `path.${name}`, message: `does not match pattern ${rule.pattern}` });
        }
        if (rule.enum && !rule.enum.includes(String(coerced))) {
          errors.push({ field: `path.${name}`, message: `must be one of ${rule.enum.join(", ")}` });
        }
      }
    }

    // — Query params —
    if (schema.query_params) {
      for (const [name, rule] of Object.entries(schema.query_params)) {
        const raw = req.query[name] as string | undefined;
        if (raw === undefined) {
          if (rule.required !== false) errors.push({ field: `query.${name}`, message: "required" });
          continue;
        }
        if (rule.enum && !rule.enum.includes(raw)) {
          errors.push({ field: `query.${name}`, message: `must be one of ${rule.enum.join(", ")}` });
        }
      }
    }

    // — Request body (JSON Schema) —
    if (schema.body && req.body !== undefined) {
      const valid = ajv.validate(schema.body, req.body);
      if (!valid && ajv.errors) {
        for (const e of ajv.errors) {
          errors.push({
            field: `body${e.instancePath ?? ""}`,
            message: e.message ?? "invalid",
          });
        }
      }
    }

    // — Headers —
    if (schema.headers) {
      for (const [name, rule] of Object.entries(schema.headers as Record<string, HeaderSchema>)) {
        const val = req.headers[name.toLowerCase()];
        if (!val) {
          if (rule.required) errors.push({ field: `header.${name}`, message: "required" });
          continue;
        }
        if (rule.pattern && !new RegExp(rule.pattern).test(String(val))) {
          errors.push({ field: `header.${name}`, message: `does not match pattern ${rule.pattern}` });
        }
      }
    }

    if (errors.length > 0) {
      res.status(400).json({ error: "Validation failed", details: errors });
      return;
    }

    next();
  };
}
