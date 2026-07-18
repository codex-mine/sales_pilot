// Mirrors the backend's app/schemas/ai.py request shapes exactly.

import { z } from "zod";
import { AI_AGENT_TYPE_CHOICES, LLM_PROVIDER_CHOICES } from "../types";

export const aiAgentFormSchema = z.object({
  name: z.string().min(1, "Name is required.").max(100),
  agent_type: z.enum(AI_AGENT_TYPE_CHOICES),
  description: z.string().max(2000).optional().or(z.literal("")),
  provider: z.enum(LLM_PROVIDER_CHOICES),
  model_name: z.string().min(1, "Model is required.").max(100),
  temperature: z.coerce.number().min(0).max(2),
  max_tokens: z.coerce.number().int().min(1).max(200_000),
  is_active: z.boolean(),
});
export type AIAgentFormValues = z.infer<typeof aiAgentFormSchema>;

export const aiSettingsFormSchema = z
  .object({
    provider: z.enum(LLM_PROVIDER_CHOICES),
    api_key: z.string().max(512).optional().or(z.literal("")),
    base_url: z.string().max(512).optional().or(z.literal("")),
  })
  .refine((value) => value.provider === "local" || Boolean(value.api_key), {
    message: "An API key is required.",
    path: ["api_key"],
  })
  .refine((value) => value.provider !== "local" || Boolean(value.base_url), {
    message: "A base URL is required for Ollama.",
    path: ["base_url"],
  });
export type AISettingsFormValues = z.infer<typeof aiSettingsFormSchema>;

export const promptVersionFormSchema = z.object({
  system_prompt: z.string().min(1, "System prompt is required."),
  user_prompt_template: z.string().min(1, "User prompt template is required."),
  variables: z.string().optional(), // comma-separated in the form, split before submit
  change_notes: z.string().max(2000).optional().or(z.literal("")),
  activate: z.boolean(),
});
export type PromptVersionFormValues = z.infer<typeof promptVersionFormSchema>;
