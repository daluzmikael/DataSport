import type { DetailTarget, LiveFeedItem } from "../types"
import { CompactGameRow } from "./cards/CompactGameRow"
import { PlayerLiveCard } from "./cards/PlayerLiveCard"
import { TeamGameCard } from "./cards/TeamGameCard"

interface LiveDashboardFeedListProps {
  items: LiveFeedItem[]
  onOpenDetail: (target: DetailTarget) => void
}

export function LiveDashboardFeedList({ items, onOpenDetail }: LiveDashboardFeedListProps) {
  return (
    <>
      {items.map((item) => {
        if (item.kind === "followed-team") {
          return (
            <TeamGameCard
              key={item.id}
              game={item}
              onOpen={() => onOpenDetail({ type: "game", id: item.id })}
            />
          )
        }
        if (item.kind === "followed-player") {
          return (
            <PlayerLiveCard
              key={item.id}
              player={item}
              onOpen={() => onOpenDetail({ type: "player", id: item.id })}
            />
          )
        }
        return (
          <CompactGameRow
            key={item.id}
            game={item}
            onOpen={() => onOpenDetail({ type: "game", id: item.id })}
          />
        )
      })}
    </>
  )
}
