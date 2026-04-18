import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "../app/App";

function renderRoute(path: string) {
  window.history.pushState({}, "", path);
  return render(<App />);
}

describe("Hackstrom frontend routes", () => {
  it("renders the pipeline page with mapped vendor queue data", async () => {
    renderRoute("/pipelines");

    expect(await screen.findByRole("heading", { name: /Pipeline/i })).toBeInTheDocument();
    expect((await screen.findAllByText("Datastream.io")).length).toBeGreaterThan(0);
    expect(screen.getByText(/Vendor Routing/i)).toBeInTheDocument();
  });

  it("renders the vendor detail workspace with review and evidence sections", async () => {
    renderRoute("/vendors/vendor-1");

    expect(await screen.findByRole("heading", { name: /Datastream\.io/i })).toBeInTheDocument();
    expect(screen.getByText(/Evidence Gaps/i)).toBeInTheDocument();
    expect(screen.getByText(/SOC2 Type II/i)).toBeInTheDocument();
    expect(screen.getByText(/Uploaded Documents/i)).toBeInTheDocument();
  });

  it("renders the report view and keeps print export available", async () => {
    renderRoute("/vendors/vendor-1/report");

    expect(await screen.findByRole("heading", { name: /Report Packet/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Print Report/i })).toBeInTheDocument();
  });

  it("falls back to polling mode on the trace page when EventSource is unavailable", async () => {
    // @ts-expect-error test override
    window.EventSource = undefined;

    renderRoute("/trace/vendor-1");

    expect(await screen.findByText(/Polling Fallback/i)).toBeInTheDocument();
    expect(screen.getByText(/review_completed/i)).toBeInTheDocument();
  });

  it("keeps approval actions read-only without a token and enables them when a token exists", async () => {
    const first = renderRoute("/audit/vendor-1");

    expect(await screen.findByRole("heading", { name: /Approval Dashboard/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Approve/i })).toBeDisabled();
    expect(screen.getByText(/Legitimate Probability/i)).toBeInTheDocument();

    first.unmount();
    window.localStorage.setItem("hackstrom.approval-token", "test-token");

    renderRoute("/audit/vendor-1");

    await waitFor(() =>
      expect(screen.getByRole("button", { name: /Approve/i })).toBeEnabled(),
    );
  });

  it("renders the compliance dashboard without a token and gates protected actions", async () => {
    renderRoute("/dashboard/compliance");

    expect(await screen.findByRole("heading", { name: /Compliance Officer Dashboard/i })).toBeInTheDocument();
    expect(screen.getByText(/Protected Surface/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Run Query/i })).toBeDisabled();
  });

  it("submits the intake form and routes to the vendor workspace", async () => {
    const user = userEvent.setup();
    window.localStorage.setItem("hackstrom.approval-token", "dev-role:admin:ops@hackstrom.local");
    renderRoute("/intake");

    await user.type(await screen.findByLabelText(/Vendor name/i), "Datastream.io");
    await user.type(screen.getByLabelText(/Service type/i), "observability");
    await user.type(screen.getByLabelText(/^Reason$/i), "Enterprise observability intake");
    await user.clear(screen.getByLabelText(/Contract value/i));
    await user.type(screen.getByLabelText(/Contract value/i), "240000");
    await user.type(screen.getByLabelText(/Vendor contact email/i), "security@datastream.io");

    const file = new File(["demo"], "security-questionnaire.pdf", {
      type: "application/pdf",
    });
    await user.upload(screen.getByLabelText(/Optional starter files/i), file);
    await user.click(screen.getByRole("button", { name: /Submit Intake/i }));

    expect(await screen.findByRole("heading", { name: /Datastream\.io/i })).toBeInTheDocument();
  });
});
