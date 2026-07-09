export default function Button({ children, variant = 'primary', className = '', ...props }) {
  const baseStyle = "font-medium py-2 px-4 rounded-xl transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-offset-1";
  
  const variants = {
    primary: "bg-primary hover:bg-blue-700 text-white focus:ring-primary",
    secondary: "bg-white hover:bg-gray-50 text-gray-700 border border-gray-200 focus:ring-gray-200",
    danger: "bg-red-600 hover:bg-red-700 text-white focus:ring-red-600",
  };

  return (
    <button className={`${baseStyle} ${variants[variant]} ${className}`} {...props}>
      {children}
    </button>
  );
}
