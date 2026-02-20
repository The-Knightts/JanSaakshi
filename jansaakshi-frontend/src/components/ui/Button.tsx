import React from 'react';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: 'primary' | 'outline';
    size?: 'sm' | 'md' | 'lg';
    className?: string;
    children: React.ReactNode;
}

export function Button({ variant = 'primary', size = 'md', className = '', children, ...props }: ButtonProps) {
    const baseStyles = 'inline-flex items-center justify-center font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50';

    const variants = {
        primary: 'bg-blue-600 text-white hover:bg-blue-700 shadow-md',
        outline: 'border border-slate-200 bg-transparent hover:bg-slate-100 text-slate-900',
    };

    const sizes = {
        sm: 'h-9 px-3 text-sm rounded-md',
        md: 'h-11 px-4 py-2 rounded-lg',
        lg: 'h-14 px-8 text-lg rounded-xl',
    };

    return (
        <button
            className={`${baseStyles} ${variants[variant]} ${sizes[size]} ${className}`}
            {...props}
        >
            {children}
        </button>
    );
}
