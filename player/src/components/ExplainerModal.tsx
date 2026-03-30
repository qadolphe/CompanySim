import ReactMarkdown from "react-markdown";

interface ExplainerModalProps {
  open: boolean;
  title: string;
  content: string;
  onClose: () => void;
}

export default function ExplainerModal({
  open,
  title,
  content,
  onClose,
}: ExplainerModalProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-2xl rounded-2xl bg-white shadow-2xl border border-gray-200 overflow-hidden">
        <div className="flex items-center justify-between px-5 py-3 border-b border-gray-200 bg-gray-50">
          <h2 className="text-sm font-bold uppercase tracking-wide text-gray-700">
            {title}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md px-2 py-1 text-gray-500 hover:bg-gray-200 hover:text-gray-700"
            aria-label="Close methodology explainer"
          >
            ×
          </button>
        </div>

        <div className="max-h-[65vh] overflow-y-auto px-5 py-4 prose prose-sm prose-slate">
          <ReactMarkdown>{content}</ReactMarkdown>
        </div>
      </div>
    </div>
  );
}
