import axios, { AxiosInstance, AxiosResponse, InternalAxiosRequestConfig } from 'axios';
import { ElMessage } from 'element-plus';

const apiClient: AxiosInstance = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request Interceptor
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('maintainwise_token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response Interceptor
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    return response.data;
  },
  (error) => {
    if (error.response) {
      const { status, data } = error.response;
      const errorCode = data?.code;
      const errorMsg = data?.message || data?.detail || '系统未知错误';

      // 10008: 强制改密拦截 (SWR-USR-004)
      if (errorCode === 10008) {
        ElMessage.warning('首次登录或安全重置，必须修改密码后方可使用系统');
        if (window.location.pathname !== '/force-change-password') {
          window.location.href = '/force-change-password';
        }
        return Promise.reject(data);
      }

      if (status === 401) {
        ElMessage.error('登录凭据已过期，请重新登录');
        localStorage.removeItem('maintainwise_token');
        localStorage.removeItem('maintainwise_user');
        if (window.location.pathname !== '/login') {
          window.location.href = '/login';
        }
        return Promise.reject(data);
      }

      if (status === 403) {
        ElMessage.error(errorMsg || '无权访问该资源 (403)');
        return Promise.reject(data);
      }

      ElMessage.error(errorMsg);
      return Promise.reject(data);
    } else {
      ElMessage.error('网络通信异常，请检查网络连接');
      return Promise.reject(error);
    }
  }
);

export default apiClient;
