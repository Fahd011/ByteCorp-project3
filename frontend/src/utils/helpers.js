// Format date to readable string
export const formatDate = (dateString) => {
  if (!dateString) return 'N/A';
  return new Date(dateString).toLocaleString();
};

// Format file size
export const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

// Get status color
export const getStatusColor = (status) => {
  switch (status?.toLowerCase()) {
    case 'idle':
      return '#6b7280';
    case 'running':
      return '#3b82f6';
    case 'completed':
      return '#10b981';
    case 'error':
      return '#ef4444';
    default:
      return '#6b7280';
  }
};

// Validate email
export const validateEmail = (email) => {
  const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return re.test(email);
};

// Validate password strength
export const validatePassword = (password) => {
  return password.length >= 6;
};

// Create CSV template
export const createCSVTemplate = () => {
  const csvContent = 'client_name,utility_co_id,utility_co_name,cred_id,cred_user,cred_password\n"RTX-Collins",704,"Duke Energy 1004",2811,"billing+rtx@sagiliti.com","Collins123!!"\n"DeLuxe",993,"Duke Energy 1004",2474,"Rena.Jordan@deluxe.com","Goodrich1!"\n"Patterson",993,"Duke Energy 1004",476,"billing-pa@patterson.com","Energy18!"';
  const blob = new Blob([csvContent], { type: 'text/csv' });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'credentials_template.csv';
  a.click();
  window.URL.revokeObjectURL(url);
};

// Debounce function
export const debounce = (func, wait) => {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
};
