import { useState, ChangeEvent, FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import { useAuth } from '../context/AuthContext';
import { validateEmail, validatePassword } from '../utils/helpers';


const Register: React.FC = () => {
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirmPassword: '',
  });
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    
    if (!validateEmail(formData.email)) {
      toast.error('Please enter a valid email address');
      return;
    }

    if (!validatePassword(formData.password)) {
      toast.error('Password must be at least 6 characters long');
      return;
    }

    if (formData.password !== formData.confirmPassword) {
      toast.error('Passwords do not match');
      return;
    }

    setLoading(true);
    
    try {
      const result = await register({
        email: formData.email,
        password: formData.password,
      });
      
      if (result.success) {
        toast.success('Registration successful!');
        navigate('/');
      } else {
        toast.error(result.error || 'Registration failed');
      }
    } catch (error) {
      toast.error('An error occurred during registration');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-container min-h-screen flex items-center justify-center bg-gradient-to-br from-indigo-500 to-purple-600 p-4">
      <div className="auth-card bg-white rounded-2xl shadow-2xl p-10 w-full max-w-md">
        <div className="auth-header text-center mb-8">
          <h1 className="auth-logo text-4xl font-bold text-slate-800 mb-2">Sagility</h1>
          <p className="auth-subtitle text-slate-500 text-base m-0">Create your account to get started.</p>
        </div>
        
        <form onSubmit={handleSubmit} className="auth-form mb-6">
          <div className="form-group mb-5">
            <label htmlFor="email" className="form-label block font-semibold text-slate-700 mb-2">
              Email Address
            </label>
            <input
              type="email"
              id="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              className="form-input w-full px-4 py-3 border-2 border-slate-200 rounded-lg text-base transition focus:outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-500/15"
              placeholder="Enter your email"
              required
            />
          </div>

          <div className="form-group mb-5">
            <label htmlFor="password" className="form-label block font-semibold text-slate-700 mb-2">
              Password
            </label>
            <input
              type="password"
              id="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              className="w-full px-4 py-3 border-2 border-slate-200 rounded-lg text-base transition focus:outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-500/15"
              placeholder="Enter your password"
              required
            />
          </div>

          <div className="mb-5">
            <label htmlFor="confirmPassword" className="form-label block font-semibold text-slate-700 mb-2">
              Confirm Password
            </label>
            <input
              type="password"
              id="confirmPassword"
              name="confirmPassword"
              value={formData.confirmPassword}
              onChange={handleChange}
              className="w-full px-4 py-3 border-2 border-slate-200 rounded-lg text-base transition focus:outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-500/15"
              placeholder="Confirm your password"
              required
            />
          </div>

          <button
            type="submit"
            className="w-full px-6 py-3 bg-gradient-to-r from-blue-500 to-blue-600 text-white rounded-lg text-base font-semibold transition disabled:opacity-60 disabled:cursor-not-allowed hover:-translate-y-0.5 hover:shadow-lg mb-4"
            disabled={loading}
          >
            {loading && <span className="auth-loading inline-block w-4 h-4 border-2 border-white/30 rounded-full border-t-white animate-spin mr-2"></span>}
            {loading ? 'Creating account...' : 'Create Account'}
          </button>
        </form>

        <div className="text-center mt-6 pt-6 border-t border-slate-200">
          <p>
            Already have an account?{' '}
            <Link to="/login" className="text-blue-500 font-medium hover:text-blue-600 hover:underline transition">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};

export default Register;
