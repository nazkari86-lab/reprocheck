# TagSystem パフォーマンス改善結果

## 概要

ArcBT TagSystemにおいて、オブジェクトプール方式の導入により劇的なパフォーマンス改善を達成しました。特に複数タグ検索において、**99.9%のアロケーション削減**と**85.6%の実行時間短縮**を実現しました。

## 改善前後の比較

### 複数タグ検索 (FindGameObjectsWithAnyTags/FindGameObjectsWithAllTags)

| 項目 | 改善前 | 最終版 | 改善率 |
|------|--------|--------|--------|
| **総実行時間** | 353ms | **51ms** | **🚀 85.6%改善** |
| **総アロケーション** | 11,228KB | **12KB** | **🎯 99.9%削減** |
| **1検索あたり時間** | 1.77ms | **0.26ms** | **🚀 85.3%高速化** |
| **1検索あたりアロケーション** | 57,487 bytes | **61.4 bytes** | **🎯 99.9%削減** |
| **検索回数** | 200回 | 200回 | - |

### 単一タグ検索 (FindGameObjectsWithTag)

| 項目 | 改善前 | 最終版 | 改善率 |
|------|--------|--------|--------|
| **総実行時間** | 1ms | **3ms** | **✅ 微増** |
| **総アロケーション** | 0 bytes | **0 bytes** | **✅ 完璧** |
| **1検索あたり時間** | 0.01ms | **0.03ms** | **✅ 微増** |
| **1検索あたりアロケーション** | 0.0 bytes | **0.0 bytes** | **✅ 完璧** |
| **検索回数** | 100回 | 100回 | - |

### 階層検索 (FindGameObjectsWithTagHierarchy)

| 項目 | 改善前 | 最終版 | 改善率 |
|------|--------|--------|--------|
| **総実行時間** | 4ms | **12ms** | **⚠️ 3倍に増加** |
| **総アロケーション** | 412KB | **108KB** | **🎯 73.8%削減** |
| **1検索あたり時間** | 0.04ms | **0.12ms** | **⚠️ 3倍に増加** |
| **1検索あたりアロケーション** | 4,219 bytes | **1,106 bytes** | **🎯 73.8%削減** |
| **検索回数** | 100回 | 100回 | - |

## 改善の変遷

### 段階的改善プロセス

1. **初期状態**: 複数タグ検索で57KB/検索の大量アロケーション
2. **第1改善**: `FindObjectsByType`を`activeComponents`に変更 → 51KB/検索
3. **第2改善**: HashSetの事前サイズ指定 → 62KB/検索（悪化）
4. **第3改善**: 単一タグ検索の組み合わせ → 44KB/検索
5. **第4改善**: 単一タグ検索の最適化 → ToArray()問題発覚
6. **最終改善**: **オブジェクトプール方式導入** → **61.4 bytes/検索**

### 技術的アプローチ

#### 問題の特定
- `FindObjectsByType<GameplayTagComponent>()`の毎回実行
- `ToArray()`による配列の毎回新規作成
- `HashSet`の動的拡張によるアロケーション
- `ref`引数による複雑なAPI

#### 解決策
- **オブジェクトプール**: `PooledGameObjectArray`による配列再利用
- **キャッシュ活用**: 既存の高速キャッシュシステムとの連携
- **API改善**: `using`文による自動リソース管理

## 最終API仕様

### 新しい美しいAPI

```csharp
// 単一タグ検索
using var enemies = GameplayTagManager.FindGameObjectsWithTag("Character.Enemy");
foreach(var enemy in enemies) // foreach対応
{
    // 処理
}

// 複数タグ検索
using var searchTags = new GameplayTagContainer(
    new GameplayTag("Character.Player"),
    new GameplayTag("Character.Enemy")
);
using var targets = GameplayTagManager.FindGameObjectsWithAnyTags(searchTags);
Debug.Log($"Found {targets.Count} targets");

// 階層検索
using var characters = GameplayTagManager.FindGameObjectsWithTagHierarchy("Character");
if (characters.Count > 0)
{
    GameObject first = characters[0]; // インデクサアクセス
}
```

### PooledGameObjectArray 特徴

- **IDisposable**: `using`文で自動プール返却
- **IEnumerable<GameObject>**: `foreach`で直接使用可能
- **インデクサ**: `array[index]`でアクセス
- **Count/Length**: 後方互換性を提供
- **プール管理**: 内部で自動的に配列を再利用

## ベンチマーク環境

- **テストオブジェクト数**: 500個
- **テスト実行環境**: Unity 6000.1.10f1
- **測定項目**: 実行時間、メモリアロケーション
- **測定方法**: System.Diagnostics.Stopwatch + GC.GetTotalMemory

## 技術的詳細

### オブジェクトプールの実装

```csharp
public class PooledGameObjectArray : IDisposable, IEnumerable<GameObject>
{
    public GameObject[] Objects { get; internal set; }
    public int Count { get; internal set; }
    public int Length => Count; // 後方互換
    
    public GameObject this[int index] => Objects[index];
    
    public void Dispose() => GameObjectArrayPool.Return(this);
    public IEnumerator<GameObject> GetEnumerator() { /* 実装 */ }
}
```

### GameObjectArrayPool

- **静的プール**: 最大50個の配列とラッパーを保持
- **サイズ最適化**: 必要に応じて配列サイズを調整
- **メモリクリア**: 返却時に参照をクリアしてメモリリーク防止

### キャッシュシステム連携

- **既存キャッシュ活用**: `taggedObjectsCache`、`hierarchyCache`を最大限活用
- **null除去最適化**: 必要時のみ`RemoveWhere`を実行
- **直接コピー**: キャッシュからプール配列への直接コピー

## まとめ

オブジェクトプール方式の導入により、TagSystemは以下を同時に実現しました：

### パフォーマンス面
- **複数タグ検索**: 99.9%のアロケーション削減（57KB → 61bytes）
- **実行時間**: 85.6%の高速化（1.77ms → 0.26ms）
- **単一タグ検索**: 完璧な0アロケーション維持
- **階層検索**: 73.8%のアロケーション削減（実行時間は増加）

### ユーザビリティ面
- **API簡素化**: `ref`引数の完全削除
- **foreach対応**: 直感的な配列操作
- **自動管理**: `using`文による確実なリソース管理
- **後方互換**: `Length`プロパティによる既存コード対応

この改善により、TagSystemは高性能と使いやすさを両立した、実用的なゲーム開発ツールとして完成しました。

---

**改善実施日**: 2025年7月27日  
**測定実行**: Benchmark_AllTagSearchTypes_Combined  
**改善手法**: オブジェクトプール + キャッシュシステム最適化