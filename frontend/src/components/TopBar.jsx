import { Link } from "react-router-dom";

export default function TopBar() {
  return (
    <header className="h-14 border-b border-border bg-card flex items-center justify-end px-6 shrink-0">
      <Link
        to="/profile"
        title="View profile"
        className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-white text-xs font-bold hover:opacity-90"
      >
        U
      </Link>
    </header>
  );
}
