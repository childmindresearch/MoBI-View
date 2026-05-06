import { render, screen } from "@testing-library/svelte";
import { describe, expect, it } from "vitest";

import Page from "../routes/+page.svelte";

describe("home page", () => {
  it("renders the MoBI-View frontend scaffold", () => {
    render(Page);

    expect(
      screen.getByRole("heading", { name: "Real-time stream visualization" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Frontend scaffold ready for ws://localhost:8765"),
    ).toBeInTheDocument();
  });
});
