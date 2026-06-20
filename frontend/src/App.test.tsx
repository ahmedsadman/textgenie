import { render, screen } from "@testing-library/react";
import App from "./App";

describe("App", () => {
  it("renders the heading", () => {
    vi.spyOn(globalThis, "fetch").mockReturnValue(new Promise(() => {}));

    render(<App />);

    expect(screen.getByText("TextGenie")).toBeInTheDocument();
  });
});
