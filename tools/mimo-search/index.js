#!/usr/bin/env node
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import OpenAI from "openai";
import { z } from "zod";

const MIMO_API_KEY = process.env.MIMO_API_KEY;
const MIMO_BASE_URL = process.env.MIMO_BASE_URL || "https://api.xiaomimimo.com/v1";

if (!MIMO_API_KEY) {
  console.error("MIMO_API_KEY environment variable is required");
  process.exit(1);
}

const client = new OpenAI({
  apiKey: MIMO_API_KEY,
  baseURL: MIMO_BASE_URL,
});

const server = new McpServer({
  name: "mimo-web-search",
  version: "1.0.0",
});

server.tool(
  "mimo_web_search",
  "Search the web using Xiaomi MiMo's web search capability. Returns search results with citations and a summarized answer.",
  {
    query: z.string().describe("The search query"),
    max_keyword: z.number().min(1).max(10).default(3).describe("Max number of search keywords per round"),
    limit: z.number().min(1).max(10).default(5).describe("Max number of search results to return"),
    force_search: z.boolean().default(true).describe("Force web search instead of letting the model decide"),
  },
  async ({ query, max_keyword, limit, force_search }) => {
    try {
      const completion = await client.chat.completions.create({
        model: "mimo-v2.5-pro",
        messages: [
          {
            role: "system",
            content: "You are a search assistant. Search the web and provide a comprehensive answer with sources. Today is " + new Date().toISOString().split("T")[0] + "."
          },
          { role: "user", content: query }
        ],
        tools: [{
          type: "web_search",
          max_keyword,
          limit,
          force_search,
        }],
        max_completion_tokens: 2048,
        temperature: 0.7,
      });

      const choice = completion.choices?.[0];
      const message = choice?.message;
      const content = message?.content || "No results found.";
      const usage = completion.usage;

      // Extract citations from annotations
      const citations = [];
      if (message?.annotations) {
        for (const ann of message.annotations) {
          if (ann.type === "url_citation") {
            citations.push({
              title: ann.title,
              url: ann.url,
              site_name: ann.site_name,
              summary: ann.summary?.slice(0, 200),
            });
          }
        }
      }

      const result = {
        answer: content,
        citations,
        usage: usage?.web_search_usage || null,
      };

      return {
        content: [{
          type: "text",
          text: JSON.stringify(result, null, 2),
        }],
      };
    } catch (err) {
      return {
        content: [{
          type: "text",
          text: `Error: ${err.message}`,
        }],
        isError: true,
      };
    }
  }
);

const transport = new StdioServerTransport();
await server.connect(transport);
