import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Incident Investigation Copilot",
  description:
    "An on-call assistant that retrieves logs, runs sandboxed diagnostics, and drafts evidence-grounded incident reports.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body style={{ fontFamily: "system-ui, sans-serif", margin: 0, padding: 0 }}>
        <div
          style={{
            background: "#fff8e1",
            color: "#7a5b00",
            padding: "0.5rem 1rem",
            fontSize: "0.85rem",
            textAlign: "center",
          }}
        >
          Architectural demonstration running on fully synthetic log data. Not
          connected to any real system.
        </div>
        {children}
      </body>
    </html>
  );
}
