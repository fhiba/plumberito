export default function PaywallModal({ onDismiss }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#1e1b13]/60">
      <div className="bg-surface border-4 border-[#1e1b13] p-8 max-w-md w-full mx-4 brutalist-shadow">
        <div className="flex items-center gap-3 mb-6">
          <span className="bg-primary-container text-white px-2 py-0.5 text-[10px] font-black uppercase tracking-tighter font-label">
            PLUMBERITO PRO
          </span>
        </div>

        <p className="font-mono text-sm leading-relaxed mb-8">
          Para poder desarrollar cosas más allá de la infraestructura es necesario tener{" "}
          <span className="font-black text-primary-container">Plumberito Pro</span>.
        </p>

        <div className="flex gap-3 justify-end">
          <button
            onClick={onDismiss}
            className="border-2 border-[#1e1b13] px-6 py-2 font-headline font-black uppercase tracking-widest text-sm hover:bg-[#1e1b13] hover:text-[#fff8ef] transition-colors"
          >
            CANCEL
          </button>
          <button
            onClick={onDismiss}
            className="bg-[#1e1b13] text-[#fff8ef] border-2 border-[#1e1b13] px-6 py-2 font-headline font-black uppercase tracking-widest text-sm hover:bg-primary-container transition-colors"
          >
            OKAY
          </button>
        </div>
      </div>
    </div>
  );
}
