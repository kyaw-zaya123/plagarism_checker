import React from 'react';

interface AlertProps {
  type: 'success' | 'warning' | 'error';
  message: string;
}

const Alert: React.FC<AlertProps> = ({ type, message }) => {
  const getBackgroundColor = () => {
    switch (type) {
      case 'success':
        return 'bg-green-100 text-green-700';
      case 'warning':
        return 'bg-yellow-100 text-yellow-700';
      case 'error':
        return 'bg-red-100 text-red-700';
      default:
        return '';
    }
  };

  return (
    <div className={`p-4 rounded-md ${getBackgroundColor()}`}>
      <p>{message}</p>
    </div>
  );
};

export default Alert;
