import React from 'react';

interface AlertDialogProps {
  title: string;
  description: string;
  confirmText: string;
  cancelText: string;
  onConfirm: () => void;
  onCancel: () => void;
}

const AlertDialog: React.FC<AlertDialogProps> = ({ title, description, confirmText, cancelText, onConfirm, onCancel }) => {
  return (
    <div className="fixed inset-0 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-white p-6 rounded-md shadow-lg">
        <h2 className="text-lg font-bold">{title}</h2>
        <p className="mt-2">{description}</p>
        <div className="mt-4 flex justify-end space-x-4">
          <button onClick={onCancel} className="px-4 py-2 text-gray-700">
            {cancelText}
          </button>
          <button onClick={onConfirm} className="px-4 py-2 bg-red-500 text-white">
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
};

export default AlertDialog;
