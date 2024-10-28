import React, { useState } from 'react';
import Alert from './ui/alert';
import AlertDialog from './ui/alert-dialog';
import Card from './ui/card';

interface ApiKey {
  id: string;
  key: string;
}

const ApiKeyManager: React.FC = () => {
  const [apiKeys, setApiKeys] = useState<ApiKey[]>([]);
  const [alert, setAlert] = useState({ message: '', type: 'success' });
  const [showDialog, setShowDialog] = useState(false);
  const [selectedKey, setSelectedKey] = useState<ApiKey | null>(null);

  const handleGenerateKey = () => {
    const newKey = { id: Date.now().toString(), key: `key-${Date.now()}` };
    setApiKeys([...apiKeys, newKey]);
    setAlert({ message: 'API key generated successfully!', type: 'success' });
  };

  const handleDeleteKey = (key: ApiKey) => {
    setSelectedKey(key);
    setShowDialog(true);
  };

  const confirmDeleteKey = () => {
    if (selectedKey) {
      setApiKeys(apiKeys.filter((key) => key.id !== selectedKey.id));
      setAlert({ message: 'API key deleted successfully!', type: 'success' });
    }
    setShowDialog(false);
  };

  return (
    <div>
      {alert.message && <Alert type={alert.type as 'success' | 'warning' | 'error'} message={alert.message} />}
      
      <button onClick={handleGenerateKey} className="bg-blue-500 text-white px-4 py-2 rounded-md">
        Generate API Key
      </button>

      <div className="mt-4 grid grid-cols-1 gap-4">
        {apiKeys.map((key) => (
          <Card key={key.id} title="API Key">
            <div className="flex justify-between items-center">
              <span>{key.key}</span>
              <button onClick={() => handleDeleteKey(key)} className="text-red-500">
                Delete
              </button>
            </div>
          </Card>
        ))}
      </div>

      {showDialog && selectedKey && (
        <AlertDialog
          title="Delete API Key"
          description={`Are you sure you want to delete the API key "${selectedKey.key}"?`}
          confirmText="Yes, delete"
          cancelText="Cancel"
          onConfirm={confirmDeleteKey}
          onCancel={() => setShowDialog(false)}
        />
      )}
    </div>
  );
};

export default ApiKeyManager;
