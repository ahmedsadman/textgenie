import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";

import { ChipInput } from "@/components/ui/chip-input";

function Harness({
  initial = [],
  suggestions = [],
}: {
  initial?: string[];
  suggestions?: string[];
}) {
  const [value, setValue] = useState<string[]>(initial);
  return (
    <ChipInput
      value={value}
      onChange={setValue}
      suggestions={suggestions}
      ariaLabel="chips"
    />
  );
}

describe("ChipInput", () => {
  it("adds a chip when Enter is pressed", async () => {
    const user = userEvent.setup();
    render(<Harness />);

    const input = screen.getByLabelText("chips");
    await user.type(input, "brac{Enter}");

    expect(
      screen.getByText("brac", { selector: "[data-slot='chip'] span" }),
    ).toBeInTheDocument();
  });

  it("treats comma as a delimiter, never embedding it in a chip", async () => {
    const user = userEvent.setup();
    render(<Harness />);

    const input = screen.getByLabelText("chips") as HTMLInputElement;
    await user.type(input, "brac,ebl");

    // Comma commits the current token, so "brac" becomes a chip and "ebl"
    // remains pending in the input — no chip text ever contains a comma.
    expect(
      screen.getByText("brac", { selector: "[data-slot='chip'] span" }),
    ).toBeInTheDocument();
    expect(input.value).toBe("ebl");
    expect(
      screen.queryByText(/,/, { selector: "[data-slot='chip'] span" }),
    ).not.toBeInTheDocument();
  });

  it("dedupes case-insensitively", async () => {
    const user = userEvent.setup();
    render(<Harness initial={["brac"]} />);

    const input = screen.getByLabelText("chips");
    await user.type(input, "BRAC{Enter}");

    const chips = screen.getAllByText(/brac/i, {
      selector: "[data-slot='chip'] span",
    });
    expect(chips).toHaveLength(1);
  });

  it("removes the last chip on Backspace when input is empty", async () => {
    const user = userEvent.setup();
    render(<Harness initial={["brac", "ebl"]} />);

    const input = screen.getByLabelText("chips");
    input.focus();
    await user.keyboard("{Backspace}");

    expect(
      screen.queryByText("ebl", { selector: "[data-slot='chip'] span" }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByText("brac", { selector: "[data-slot='chip'] span" }),
    ).toBeInTheDocument();
  });

  it("removes a chip when its × button is clicked", async () => {
    const user = userEvent.setup();
    render(<Harness initial={["brac", "ebl"]} />);

    await user.click(screen.getByLabelText("Remove brac"));

    expect(
      screen.queryByText("brac", { selector: "[data-slot='chip'] span" }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByText("ebl", { selector: "[data-slot='chip'] span" }),
    ).toBeInTheDocument();
  });

  it("filters suggestions out of the dropdown once chipped", async () => {
    const user = userEvent.setup();
    render(<Harness initial={["brac"]} suggestions={["brac", "ebl", "gp"]} />);

    const input = screen.getByLabelText("chips");
    await user.click(input);

    expect(
      screen.queryByRole("option", { name: "brac" }),
    ).not.toBeInTheDocument();
    expect(screen.getByRole("option", { name: "ebl" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "gp" })).toBeInTheDocument();
  });
});
