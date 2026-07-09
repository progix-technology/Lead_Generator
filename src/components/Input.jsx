export default function Input({ label, type = 'text', className = '', ...props }) {
  return (
    <div className={`w-full ${className}`}>
      {label && <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>}
      <input
        type={type}
        className="w-full px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all duration-200"
        {...props}
      />
    </div>
  );
}
