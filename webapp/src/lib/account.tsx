import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { api, type FlowAccount, type Health } from "../api/client";

/**
 * Tài khoản Flow đang đăng nhập trong Chrome — nguồn duy nhất cho toàn app.
 *
 * Đổi account là đổi luôn tập dữ liệu được phép xem (dự án của account cũ bị ẩn và mọi thao
 * tác lên nó trả 403), nên phải phát hiện sớm để đưa người dùng về danh sách dự án thay vì
 * để họ ngồi trong một dự án không còn thuộc về mình.
 *
 * Poll `/health` chứ không dùng WebSocket — cùng lý do với JobsContext: proxy ws của Vite ở
 * chế độ dev hay hỏng. Endpoint này cục bộ và không hỏi ngược extension nên rẻ.
 */
const POLL_MS = 5000;

type Ctx = {
  health: Health | null;
  account: FlowAccount | null;
  /** Tăng mỗi lần Chrome đổi HẲN sang một tài khoản khác — dùng làm key để reset màn hình. */
  switches: number;
};

const AccountCtx = createContext<Ctx>({ health: null, account: null, switches: 0 });

export function AccountProvider({ children }: { children: ReactNode }) {
  const [health, setHealth] = useState<Health | null>(null);
  const [switches, setSwitches] = useState(0);
  const lastId = useRef<string | null>(null);

  useEffect(() => {
    let alive = true;
    const tick = async () => {
      let h: Health | null = null;
      try {
        h = await api.health();
      } catch {
        /* agent chưa lên / mất mạng — giữ trạng thái cũ, thử lại lượt sau */
      }
      if (!alive) return;
      setHealth(h);
      const id = h?.account?.id ?? null;
      // CHỈ tính là đổi account khi đi từ một tài khoản đã biết sang một tài khoản đã biết
      // khác. Mất extension (id → null) không phải đổi account, và đá người dùng ra khỏi dự
      // án đang mở chỉ vì health lỗi một nhịp là hỏng việc.
      if (id) {
        if (lastId.current && id !== lastId.current) setSwitches((n) => n + 1);
        lastId.current = id;
      }
    };
    tick();
    const t = setInterval(tick, POLL_MS);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, []);

  return (
    <AccountCtx.Provider value={{ health, account: health?.account ?? null, switches }}>
      {children}
    </AccountCtx.Provider>
  );
}

export const useFlowAccount = () => useContext(AccountCtx);
