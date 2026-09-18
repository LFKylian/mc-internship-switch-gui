import { useState } from 'react';
import { UsersPanel } from './UsersPanel';
import { GroupsPanel } from './GroupsPanel';

export function UserGroupTabsPanel() {
  const [activeTab, setActiveTab] = useState<'users' | 'groups'>('users');

  return (
    <div className="panel-card">
      <div className="panel-tab-header">
        <button
          type="button"
          className={`panel-tab-btn ${activeTab === 'users' ? 'active' : ''}`}
          onClick={() => setActiveTab('users')}
        >
          UTILISATEURS
        </button>
        <button
          type="button"
          className={`panel-tab-btn ${activeTab === 'groups' ? 'active' : ''}`}
          onClick={() => setActiveTab('groups')}
        >
          GROUPES
        </button>
      </div>

      <div className="panel-tab-body">
        {activeTab === 'users' ? <UsersPanel /> : <GroupsPanel />}
      </div>
    </div>
  );
}